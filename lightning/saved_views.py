"""Named, validated register filters shared by the register and its report/export."""
from __future__ import annotations

import calendar
from datetime import date

from lightning.categories.domain import Movement
from lightning.core.dates import fmt_date, parse_date, today
from lightning.core.errors import ConflictError, NotFoundError, ValidationError
from lightning.core.dates import now_iso
from lightning.transactions.tags import normalize as normal_tag

MAX_VIEWS = 50
MAX_LABEL = 64
PRESETS = {"all_time", "this_month", "last_month", "year_to_date", "custom"}
_SEARCH_LIMIT = 200


class SavedViewService:
    """CRUD and date/filter resolution for saved register views.

    A stored view contains only the supported register fields: date preset/range, search text,
    exact tag, and category. Account scope is stored separately and must match at read time.
    """

    def __init__(self, db, categories, transactions, reporting):
        self.db, self.categories, self.transactions, self.reporting = db, categories, transactions, reporting

    @staticmethod
    def _view_id(value) -> int:
        text = str(value or "").strip()
        if not text.isdigit() or not 0 < int(text) <= 2**63 - 1:
            raise ValidationError("Choose a valid saved view.")
        return int(text)

    @staticmethod
    def normalize(filters: dict, *, account_id: int | None = None) -> dict:
        preset = str(filters.get("preset") or "all_time").strip()
        if preset not in PRESETS:
            raise ValidationError("Choose a supported date period.")
        start = end = None
        if preset == "custom":
            try:
                start, end = fmt_date(parse_date(filters.get("date_from"))), fmt_date(parse_date(filters.get("date_to")))
            except ValidationError:
                raise ValidationError("Enter both valid dates for the custom period.") from None
            if end < start:
                raise ValidationError("End date must be on or after the start date.")
        query = " ".join(str(filters.get("q") or "").split())
        if len(query) > _SEARCH_LIMIT:
            raise ValidationError("Keep search text within 200 characters.")
        tag = normal_tag(str(filters.get("tag") or ""))
        category_raw = str(filters.get("category_id") or "").strip()
        if category_raw and (not category_raw.isdigit() or not 0 < int(category_raw) <= 2**63 - 1):
            raise ValidationError("Choose a valid category.")
        cat_id = int(category_raw) if category_raw else None
        if account_id is not None and (not isinstance(account_id, int) or account_id < 1):
            raise ValidationError("Choose a valid account.")
        return {"account_id": account_id, "preset": preset, "date_from": start, "date_to": end,
                "q": query, "tag": tag, "category_id": cat_id}

    def save(self, name: str, filters: dict, account_id: int | None = None) -> int:
        label = " ".join(str(name or "").split())
        if not label or len(label) > MAX_LABEL or any(ord(ch) < 32 for ch in label):
            raise ValidationError(f"Name the view in 1 to {MAX_LABEL} characters.")
        definition = self.normalize(filters, account_id=account_id)
        if definition["category_id"]:
            self.categories.get(definition["category_id"])
        if self.db.one("SELECT 1 FROM saved_views WHERE account_id IS ? AND name=? COLLATE NOCASE",
                       (account_id, label)):
            raise ConflictError("A saved view with that name already exists here.")
        current = self.db.scalar("SELECT COUNT(*) FROM saved_views WHERE account_id IS ?", (account_id,)) or 0
        if current >= MAX_VIEWS:
            raise ValidationError(f"Keep no more than {MAX_VIEWS} saved views for this register.")
        now = now_iso()
        cur = self.db.execute(
            "INSERT INTO saved_views(name,account_id,preset,date_from,date_to,query_text,tag,category_id,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (label, account_id, definition["preset"], definition["date_from"], definition["date_to"],
             definition["q"], definition["tag"], definition["category_id"], now, now))
        return int(cur.lastrowid)

    def list(self, account_id: int | None = None) -> list[dict]:
        rows = self.db.all("SELECT * FROM saved_views WHERE account_id IS ? ORDER BY name COLLATE NOCASE,id", (account_id,))
        return [self._definition(row) | {"id": row["id"], "name": row["name"]} for row in rows]

    def get(self, view_id, account_id: int | None = None) -> dict:
        view_id = self._view_id(view_id)
        row = self.db.one("SELECT * FROM saved_views WHERE id=? AND account_id IS ?", (view_id, account_id))
        if row is None:
            raise NotFoundError("That saved view is no longer available.")
        return self._definition(row) | {"id": row["id"], "name": row["name"]}

    def delete(self, view_id, account_id: int | None = None) -> None:
        view_id = self._view_id(view_id)
        cur = self.db.execute("DELETE FROM saved_views WHERE id=? AND account_id IS ?", (view_id, account_id))
        if cur.rowcount != 1:
            raise NotFoundError("That saved view is no longer available.")

    @staticmethod
    def _definition(row) -> dict:
        return {"account_id": row["account_id"], "preset": row["preset"], "date_from": row["date_from"],
                "date_to": row["date_to"], "q": row["query_text"], "tag": row["tag"],
                "category_id": row["category_id"]}

    @staticmethod
    def dates(definition: dict, on: date | None = None) -> tuple[str, str]:
        day = on or today()
        preset = definition["preset"]
        if preset == "all_time":
            return "1900-01-01", "9999-12-31"
        if preset == "custom":
            return definition["date_from"], definition["date_to"]
        if preset == "year_to_date":
            return f"{day.year:04d}-01-01", fmt_date(day)
        if preset == "last_month":
            year, month = (day.year - 1, 12) if day.month == 1 else (day.year, day.month - 1)
        else:
            year, month = day.year, day.month
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"

    def rows(self, definition: dict):
        """Resolve one definition into the exact transaction rows consumed by report and export."""
        start, end = self.dates(definition)
        account_id, query, tag, cat_id = (definition[k] for k in ("account_id", "q", "tag", "category_id"))
        ids = self.transactions.search_ids(query) if query and query.casefold() != ("#" + tag).casefold() else None
        if tag:
            tagged = self.transactions.tag_transaction_ids(tag)
            ids = tagged if ids is None else ids & tagged
        if cat_id:
            category = self.categories.get(cat_id)
            tree = self.categories.tree(Movement.OUTFLOW)
            children: dict[int, list[int]] = {}
            for item in tree:
                if item.parent_id:
                    children.setdefault(item.parent_id, []).append(item.id)
            category_ids, pending = {category.id}, [category.id]
            while pending:
                for child in children.get(pending.pop(), []):
                    if child not in category_ids:
                        category_ids.add(child); pending.append(child)
            by_category = self.reporting.category_transaction_ids(category_ids)
            ids = by_category if ids is None else ids & by_category
        return self.reporting.register(account_id, start, end, ids)

    def report(self, definition: dict) -> dict:
        rows = self.rows(definition)
        ids = {row.txn_id for row in rows}
        money_in, money_out = self.reporting.money_in_out(ids) if ids else (0, 0)
        return {"rows": rows, "date_from": self.dates(definition)[0], "date_to": self.dates(definition)[1],
                "count": len(ids), "money_in": money_in, "money_out": money_out}
