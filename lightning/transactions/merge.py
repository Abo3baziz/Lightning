"""Preview and safely merge two duplicate ordinary cash transactions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from lightning.core.errors import NotFoundError, ValidationError
from lightning.core.refs import DocType
from .tags import tags_in


ALLOWED_DEPENDENCIES = {"ledger_entries", "bank_import_rows", "planned_payments", "reserve_transaction_links"}


@dataclass(frozen=True)
class MergePreview:
    keep: object
    drop: object
    fingerprint: str
    dependencies: tuple[str, ...]


class MergeService:
    def __init__(self, transactions):
        self.tx = transactions
        self.db = transactions.db

    def preview(self, keep_id: int, drop_id: int) -> MergePreview:
        keep, drop = self._validate_pair(keep_id, drop_id)
        return MergePreview(keep, drop, self._fingerprint(keep.id, drop.id),
                            tuple(self._dependency_summary(drop.id)))

    def merge(self, keep_id: int, drop_id: int, fingerprint: str):
        if not fingerprint:
            raise ValidationError("Review the merge preview before confirming.")
        with self.db.transaction(undo_label="Merge duplicate transactions"):
            current = self.preview(keep_id, drop_id)
            if current.fingerprint != fingerprint:
                raise ValidationError("These transactions changed after the preview. Review the merge again.")
            keep, drop = current.keep, current.drop
            keep_id, drop_id = keep.id, drop.id
            self._preserve_header_and_categories(keep, drop)
            self._move_supported_links(keep_id, drop_id)
            self.tx.void(drop_id, f"Merged into {keep.ref}")
            self.tx.audit.record("transaction", keep_id, "merge", f"Merged duplicate {drop.ref} into {keep.ref}")
        return self.tx.get(keep_id)

    def _validate_pair(self, keep_id, drop_id):
        if any(isinstance(value, bool) or not isinstance(value, int) or
               not 1 <= value <= 2**63 - 1 for value in (keep_id, drop_id)):
            raise ValidationError("Choose two valid transactions.")
        if keep_id == drop_id:
            raise ValidationError("Choose two different transactions.")
        keep = self.tx.get(keep_id)
        drop = self.tx.get(drop_id)
        if keep is None or drop is None:
            raise NotFoundError("Transaction not found.")
        for txn in (keep, drop):
            if txn.is_void:
                raise ValidationError("Only active transactions can be merged.")
            if txn.type not in {DocType.IN, DocType.OUT, DocType.TRF}:
                raise ValidationError("Only ordinary money in, money out, and transfer entries can be merged.")
        if abs((date.fromisoformat(keep.date) - date.fromisoformat(drop.date)).days) > 7:
            raise ValidationError("Transactions must be dated within seven days of each other.")
        keep_sig = self._cash_signature(keep)
        drop_sig = self._cash_signature(drop)
        if not keep_sig or keep_sig != drop_sig:
            raise ValidationError("These transactions do not have identical cash effects.")
        if self._is_reconciled(keep_id) or self._is_reconciled(drop_id):
            raise ValidationError("Unlock the checked account history before merging these transactions.")
        refs = {txn_id: self.db.scalar(
            "SELECT COUNT(*) FROM bank_import_rows WHERE transaction_id=? AND bank_reference IS NOT NULL AND trim(bank_reference)<>''",
            (txn_id,)) for txn_id in (keep_id, drop_id)}
        if bool(refs[keep_id]) != bool(refs[drop_id]) and not refs[keep_id]:
            keep, drop = drop, keep
            keep_id, drop_id = keep.id, drop.id
        self._check_dependencies(keep_id, drop_id)
        self._check_link_collisions(keep_id, drop_id)
        return keep, drop

    def _cash_signature(self, txn):
        rows = self.db.all(
            "SELECT le.account_id,le.asset_id,le.quantity_e6,le.effect,le.owner_id,fa.is_cash "
            "FROM ledger_entries le JOIN financial_assets fa ON fa.id=le.asset_id WHERE le.transaction_id=?",
            (txn.id,))
        if not rows or any(not row["is_cash"] for row in rows):
            return ()
        return tuple(sorted((int(r["account_id"]), int(r["asset_id"]), int(r["quantity_e6"]),
                             r["effect"], int(r["owner_id"] or 0)) for r in rows))

    def _is_reconciled(self, txn_id):
        return bool(self.db.scalar(
            "SELECT 1 FROM ledger_entries le JOIN reconciled_through r ON r.account_id=le.account_id "
            "WHERE le.transaction_id=? AND le.date<=r.date LIMIT 1", (txn_id,)))

    def _fk_columns(self):
        result = {}
        for table_row in self.db.all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            table = table_row["name"]
            for fk in self.db.all(f'PRAGMA foreign_key_list("{table}")'):
                if fk["table"] == "transactions":
                    result.setdefault(table, []).append(fk["from"])
        return result

    def _dependency_summary(self, txn_id):
        links = []
        for table, columns in self._fk_columns().items():
            for col in columns:
                count = self.db.scalar(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}"=?', (txn_id,)) or 0
                if count:
                    links.append(f"{table}:{count}")
        return links

    def _check_dependencies(self, keep_id, drop_id):
        for table, columns in self._fk_columns().items():
            if table not in ALLOWED_DEPENDENCIES:
                for col in columns:
                    if self.db.scalar(f'SELECT 1 FROM "{table}" WHERE "{col}"=? LIMIT 1', (drop_id,)):
                        raise ValidationError("This transaction has linked records that cannot be moved safely.")

    def _check_link_collisions(self, keep_id, drop_id):
        linked = int(self.db.scalar("SELECT COALESCE(SUM(amount_e6),0) FROM reserve_transaction_links "
                                    "WHERE transaction_id IN (?,?)", (keep_id, drop_id)) or 0)
        if linked:
            capacity = int(self.db.scalar("SELECT COALESCE(-SUM(amount_base_e6),0) FROM ledger_entries "
                                         "WHERE transaction_id=? AND effect='OUTFLOW' AND owner_id IS NULL",
                                         (keep_id,)) or 0)
            if linked > capacity:
                raise ValidationError("Reserve links exceed this expense. Resolve those links before merging.")
        if self.db.scalar(
            "SELECT 1 FROM bank_import_rows d JOIN bank_import_rows k ON k.batch_id=d.batch_id "
            "AND k.account_id=d.account_id WHERE d.transaction_id=? AND k.transaction_id=? "
            "AND d.status IN ('POSTED','LINKED') AND k.status IN ('POSTED','LINKED') LIMIT 1",
            (drop_id, keep_id)):
            raise ValidationError("Both transactions are already linked to the same imported account row batch.")
        if self.db.scalar("SELECT 1 FROM planned_payments WHERE transaction_id=?", (drop_id,)) and \
                self.db.scalar("SELECT 1 FROM planned_payments WHERE transaction_id=?", (keep_id,)):
            raise ValidationError("Both transactions are linked to planned payments. Resolve those links first.")
        if self.db.scalar(
            "SELECT 1 FROM reserve_transaction_links d JOIN reserve_transaction_links k ON k.reserve_id=d.reserve_id "
            "WHERE d.transaction_id=? AND k.transaction_id=? LIMIT 1", (drop_id, keep_id)):
            raise ValidationError("Both transactions are linked to the same reserve. Resolve those links first.")

    def _fingerprint(self, keep_id, drop_id):
        tables = ["transactions", "ledger_entries", "bank_import_rows", "planned_payments",
                  "reserve_transaction_links"]
        snapshot = {}
        for table in tables:
            if table == "transactions":
                rows = self.db.all("SELECT * FROM transactions WHERE id IN (?,?) ORDER BY id", (keep_id, drop_id))
            elif table == "ledger_entries":
                rows = self.db.all("SELECT * FROM ledger_entries WHERE transaction_id IN (?,?) ORDER BY transaction_id,line_no",
                                   (keep_id, drop_id))
            elif table == "bank_import_rows":
                rows = self.db.all("SELECT * FROM bank_import_rows WHERE transaction_id IN (?,?) ORDER BY id",
                                   (keep_id, drop_id))
            elif table == "planned_payments":
                rows = self.db.all("SELECT * FROM planned_payments WHERE transaction_id IN (?,?) ORDER BY id",
                                   (keep_id, drop_id))
            else:
                rows = self.db.all("SELECT * FROM reserve_transaction_links WHERE transaction_id IN (?,?) ORDER BY id",
                                   (keep_id, drop_id))
            snapshot[table] = [dict(row) for row in rows]
        snapshot["other_links"] = self._dependency_summary(drop_id)
        packed = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(packed.encode("utf-8")).hexdigest()

    def _preserve_header_and_categories(self, keep, drop):
        header = self.db.one("SELECT counterparty_id FROM transactions WHERE id=?", (keep.id,))
        dropped = self.db.one("SELECT counterparty_id FROM transactions WHERE id=?", (drop.id,))
        cp = keep.counterparty or drop.counterparty
        cp_id = header["counterparty_id"] if keep.counterparty else dropped["counterparty_id"] or header["counterparty_id"]
        notes = keep.notes or drop.notes
        if keep.notes and drop.notes:
            missing_tags = [tag for tag in tags_in(drop.notes) if tag not in tags_in(keep.notes)]
            if missing_tags:
                notes = f"{keep.notes.rstrip()} {' '.join('#' + tag for tag in missing_tags)}".strip()
        if cp != keep.counterparty or cp_id != header["counterparty_id"] or notes != keep.notes:
            self.db.execute("UPDATE transactions SET counterparty=?,counterparty_id=?,notes=?,updated_at=datetime('now') WHERE id=?",
                            (cp, cp_id, notes, keep.id))
        keep_lines = self.db.all("SELECT id,account_id,asset_id,quantity_e6,effect,owner_id,category_id FROM ledger_entries "
                                 "WHERE transaction_id=? ORDER BY line_no", (keep.id,))
        drop_lines = self.db.all("SELECT account_id,asset_id,quantity_e6,effect,owner_id,category_id FROM ledger_entries "
                                 "WHERE transaction_id=? ORDER BY line_no", (drop.id,))
        grouped = {}
        for row in drop_lines:
            sig = (row["account_id"], row["asset_id"], row["quantity_e6"], row["effect"], row["owner_id"])
            grouped.setdefault(sig, []).append(row["category_id"])
        seen = {}
        for row in keep_lines:
            sig = (row["account_id"], row["asset_id"], row["quantity_e6"], row["effect"], row["owner_id"])
            pos = seen.get(sig, 0)
            seen[sig] = pos + 1
            incoming = grouped[sig][pos]
            if row["category_id"] is None and incoming is not None:
                # Duplicate signature lines with different categories are too ambiguous to transfer.
                if len(set(grouped[sig])) > 1:
                    raise ValidationError("Categories on matching split lines are ambiguous; resolve them before merging.")
                self.db.execute("UPDATE ledger_entries SET category_id=? WHERE id=?", (incoming, row["id"]))

    def _move_supported_links(self, keep_id, drop_id):
        self.db.execute("UPDATE bank_import_rows SET transaction_id=? WHERE transaction_id=?", (keep_id, drop_id))
        self.db.execute("UPDATE planned_payments SET transaction_id=? WHERE transaction_id=?", (keep_id, drop_id))
        self.db.execute("UPDATE reserve_transaction_links SET transaction_id=? WHERE transaction_id=?", (keep_id, drop_id))
