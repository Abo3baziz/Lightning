"""Explicit links between expected certificate interest and posted bank receipts.

Receipts stay ordinary transactions. This service stores only the reconciliation link and the
expected amount shown when it was confirmed; every read checks the linked transaction again.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from lightning.accounts.domain import AccountType
from lightning.core.dates import fmt_date, parse_date, today, now_iso
from lightning.core.errors import ConflictError, NotFoundError, ValidationError
from lightning.core.money import from_e6, to_e6
from lightning.core.refs import DocType
from lightning.core.ledger import Effect
from lightning.transactions.domain import TxnStatus

MAX_CONFIRMATIONS = 50


class DepositReceiptService:
    def __init__(self, db, deposits, transactions, accounts, reporting=None):
        self.db, self.deposits, self.transactions, self.accounts = db, deposits, transactions, accounts
        self.reporting = reporting

    def _certificate(self, certificate_id):
        text = str(certificate_id or "").strip()
        if not text.isdigit() or int(text) < 1:
            raise ValidationError("Choose a valid certificate.")
        return self.deposits.certificate(int(text))

    def _interest_occurrence(self, certificate_id: int, event_date: str, as_of=None):
        certificate = self._certificate(certificate_id)
        terms = certificate.terms
        purchase = self.transactions.get(terms.purchase_transaction_id)
        if purchase.status != TxnStatus.POSTED:
            raise ValidationError("The certificate purchase is no longer posted.")
        occurrence_date = parse_date(event_date, "event_date")
        if as_of is not None and occurrence_date > parse_date(as_of, "as_of"):
            raise ValidationError("Only an expected payout dated today or earlier can be confirmed.")
        redeemed = self.db.scalar(
            "SELECT t.date FROM cd_redemptions r JOIN transactions t ON t.id=r.transaction_id "
            "WHERE r.certificate_id=? AND t.status='POSTED' ORDER BY t.date LIMIT 1", (terms.id,))
        if redeemed and occurrence_date > parse_date(redeemed):
            raise ValidationError("That payout falls after this certificate was redeemed.")
        first = parse_date(terms.start_date) - timedelta(days=1)
        events = self.deposits._certificate_events(terms, first, occurrence_date)
        event = next((item for item in events if item.kind == "INTEREST" and item.date == fmt_date(occurrence_date)), None)
        if event is None:
            raise ValidationError("That date is not an expected simple-interest payout for this certificate.")
        return certificate, event

    def _event_row(self, certificate_id: int, event_date: str, *, create: bool = False):
        row = self.db.one("SELECT * FROM cd_interest_receipt_events WHERE certificate_id=? AND event_date=?",
                          (certificate_id, event_date))
        if row is None and create:
            _, event = self._interest_occurrence(certificate_id, event_date)
            account_id = event.account_id
            self.db.execute(
                "INSERT INTO cd_interest_receipt_events(certificate_id,event_date,destination_account_id,"
                "expected_amount_e6,created_at) VALUES (?,?,?,?,?)",
                (certificate_id, event_date, account_id, to_e6(event.amount), now_iso()))
            row = self.db.one("SELECT * FROM cd_interest_receipt_events WHERE certificate_id=? AND event_date=?",
                              (certificate_id, event_date))
        return row

    def _valid_receipt(self, transaction_id: int, event_row, link_row=None, as_of=None) -> tuple[Decimal | None, str]:
        try:
            txn = self.transactions.get(int(transaction_id))
        except (NotFoundError, ValueError, TypeError):
            return None, "The linked transaction no longer exists."
        if txn.status != TxnStatus.POSTED:
            return None, "The linked transaction is no longer posted."
        if txn.type != DocType.IN:
            return None, "The linked transaction is no longer a money-in entry."
        if txn.date > fmt_date(parse_date(as_of or today(), "as_of")):
            return None, "The linked transaction is dated after the review date."
        account = self.accounts.get(event_row["destination_account_id"])
        if account.account_type != AccountType.BANK or not account.active:
            return None, "The payout destination is no longer an active bank account."
        certificate = self._certificate(event_row["certificate_id"])
        portfolio = self.accounts.get(certificate.terms.account_id)
        if account.currency != portfolio.currency:
            return None, "The payout account currency no longer matches the certificate."
        lines = [line for line in txn.lines if line.account_id == account.id and line.owner_id is None
                 and line.effect == Effect.INFLOW and line.quantity > 0]
        amount = sum((line.quantity for line in lines), Decimal("0"))
        if not lines or amount <= 0:
            return None, "The linked entry is no longer an owned bank cash inflow."
        if link_row is not None and (amount != from_e6(link_row["amount_e6"])
                                     or txn.date != link_row["transaction_date"]):
            return None, "The linked receipt was edited after it was confirmed. Review and match it again."
        return amount, ""

    def _links(self, event_id: int):
        return self.db.all("SELECT * FROM cd_interest_receipt_links WHERE event_id=? ORDER BY id",
                           (event_id,))

    def _occurrence_data(self, event_row, as_of=None) -> dict:
        valid, attention = [], []
        for link in self._links(event_row["id"]):
            amount, reason = self._valid_receipt(link["transaction_id"], event_row, link, as_of)
            if amount is None:
                attention.append({"transaction_id": link["transaction_id"], "reason": reason})
            else:
                txn = self.transactions.get(int(link["transaction_id"]))
                valid.append({"transaction_id": txn.id, "ref": txn.ref, "date": txn.date, "amount": amount})
        received = sum((item["amount"] for item in valid), Decimal("0"))
        expected = from_e6(event_row["expected_amount_e6"])
        return {"id": event_row["id"], "certificate_id": event_row["certificate_id"],
                "event_date": event_row["event_date"], "destination_account_id": event_row["destination_account_id"],
                "expected": expected, "received": received, "remaining": max(Decimal("0"), expected - received),
                "receipts": valid, "attention": attention}

    def candidates(self, certificate_id: int, event_date: str, as_of=None) -> list[dict]:
        certificate, event = self._interest_occurrence(certificate_id, event_date)
        account = self.accounts.get(event.account_id)
        if account.account_type != AccountType.BANK or not account.active:
            return []
        rows = self.db.all(
            "SELECT t.id,t.ref,t.date,t.description,SUM(le.quantity_e6) amount_e6 FROM transactions t "
            "JOIN ledger_entries le ON le.transaction_id=t.id JOIN accounts a ON a.id=le.account_id "
            "WHERE t.status='POSTED' AND t.type='IN' AND le.account_id=? AND a.account_type='BANK' "
            "AND a.active=1 AND a.currency=? AND le.owner_id IS NULL AND le.effect='INFLOW' AND le.quantity_e6>0 "
            "AND t.date<=? AND NOT EXISTS (SELECT 1 FROM cd_interest_receipt_links rl WHERE rl.transaction_id=t.id) "
            "AND NOT EXISTS (SELECT 1 FROM reimbursement_receipts rr WHERE rr.receipt_id=t.id) "
            "GROUP BY t.id,t.ref,t.date,t.description ORDER BY t.date DESC,t.id DESC LIMIT 500",
            (event.account_id, account.currency, fmt_date(parse_date(as_of or today(), "as_of"))))
        return [{"id": row["id"], "ref": row["ref"], "date": row["date"],
                 "description": row["description"], "amount": from_e6(row["amount_e6"])} for row in rows]

    def confirm(self, certificate_id: int, event_date: str, transaction_ids, as_of=None) -> dict:
        certificate, event = self._interest_occurrence(certificate_id, event_date, as_of or today())
        raw_ids = list(transaction_ids or [])
        if not raw_ids or len(raw_ids) > MAX_CONFIRMATIONS:
            raise ValidationError(f"Select between 1 and {MAX_CONFIRMATIONS} bank receipts.")
        ids = []
        for value in raw_ids:
            text = str(value).strip()
            if not text.isdigit() or int(text) < 1:
                raise ValidationError("Choose valid bank receipts.")
            ids.append(int(text))
        if len(set(ids)) != len(ids):
            raise ValidationError("A bank receipt can be selected only once.")
        with self.db.transaction():
            event_row = self._event_row(certificate_id, event.date, create=True)
            existing = {int(row["transaction_id"]) for row in self._links(event_row["id"])}
            for transaction_id in ids:
                if self.db.scalar("SELECT 1 FROM reimbursement_receipts WHERE receipt_id=?", (transaction_id,)):
                    raise ConflictError("This receipt is already linked to a reimbursement claim.")
                if transaction_id in existing:
                    raise ConflictError("That receipt is already linked to this payout.")
                used = self.db.one("SELECT 1 FROM cd_interest_receipt_links WHERE transaction_id=?", (transaction_id,))
                if used:
                    raise ConflictError("A bank receipt can be matched to only one certificate payout.")
                amount, reason = self._valid_receipt(transaction_id, event_row, as_of=as_of or today())
                if amount is None:
                    raise ValidationError(reason)
                txn = self.transactions.get(transaction_id)
                self.db.execute("INSERT INTO cd_interest_receipt_links(event_id,transaction_id,amount_e6,"
                                "transaction_date,linked_at) VALUES (?,?,?,?,?)",
                                (event_row["id"], transaction_id, to_e6(amount), txn.date, now_iso()))
        return self._occurrence_data(self._event_row(certificate_id, event.date))

    def remove(self, certificate_id: int, event_date: str, transaction_id) -> None:
        certificate = self._certificate(certificate_id)
        event_date = fmt_date(parse_date(event_date, "event_date"))
        text = str(transaction_id or "").strip()
        if not text.isdigit() or int(text) < 1:
            raise ValidationError("Choose a valid bank receipt.")
        row = self._event_row(certificate.terms.id, event_date)
        if row is None:
            raise NotFoundError("That receipt confirmation is no longer available.")
        deleted = self.db.execute("DELETE FROM cd_interest_receipt_links WHERE event_id=? AND transaction_id=?",
                                  (row["id"], int(text)))
        if deleted.rowcount != 1:
            raise NotFoundError("That receipt confirmation is no longer available.")

    def expected_past(self, account_id: int, as_of=None) -> list[dict]:
        day = parse_date(as_of or today(), "as_of")
        output = []
        for certificate in self.deposits.list_certificates(account_id):
            terms = certificate.terms
            purchase = self.transactions.get(terms.purchase_transaction_id)
            if purchase.status != TxnStatus.POSTED:
                continue
            first = parse_date(terms.start_date) - timedelta(days=1)
            redeemed = self.db.scalar(
                "SELECT t.date FROM cd_redemptions r JOIN transactions t ON t.id=r.transaction_id "
                "WHERE r.certificate_id=? AND t.status='POSTED' ORDER BY t.date LIMIT 1", (terms.id,))
            horizon = min(day, parse_date(redeemed)) if redeemed else day
            event_rows = {row["event_date"]: row for row in self.db.all(
                "SELECT * FROM cd_interest_receipt_events WHERE certificate_id=?", (terms.id,))}
            for event in self.deposits._certificate_events(terms, first, horizon):
                if event.kind != "INTEREST":
                    continue
                row = event_rows.get(event.date)
                if row is None:
                    output.append({"id": None, "certificate_id": terms.id, "certificate_name": terms.name,
                                   "event_date": event.date, "destination_account_id": event.account_id,
                                   "expected": event.amount, "received": Decimal("0"), "remaining": event.amount,
                                   "receipts": [], "attention": []})
                else:
                    output.append(self._occurrence_data(row, day) | {"certificate_name": terms.name})
        return sorted(output, key=lambda item: (item["event_date"], item["certificate_id"]))

    def attention(self, day=None) -> list[dict]:
        as_of = parse_date(day or today(), "as_of")
        issues = []
        for account in self.accounts.list(active_only=True):
            if account.account_type != AccountType.DEPOSIT:
                continue
            for occurrence in self.expected_past(account.id, as_of):
                if occurrence["remaining"] > 0 or occurrence["attention"]:
                    issues.append(occurrence)
        return issues

    def adjust_events(self, events, as_of=None):
        """Subtract currently valid linked cash from future INTEREST projections; invalid links stay visible to attention()."""
        adjusted = []
        day = parse_date(as_of or today(), "as_of")
        for event in events:
            if (getattr(event, "source", "CD") != "CD" or getattr(event, "kind", None) != "INTEREST"
                    or getattr(event, "certificate_id", None) is None):
                adjusted.append(event)
                continue
            row = self._event_row(event.certificate_id, event.date)
            if row is None:
                adjusted.append(event)
                continue
            data = self._occurrence_data(row, day)
            remaining = max(Decimal("0"), event.amount - data["received"])
            if remaining > 0:
                adjusted.append(replace(event, amount=remaining))
        return adjusted
