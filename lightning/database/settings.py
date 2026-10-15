"""Key/value settings (base currency, ...)."""

from __future__ import annotations

from lightning.core.dates import now_iso
from lightning.core.memo import request_cached

from .connection import Database

DEFAULTS = {
    "base_currency": "EGP",
}


@request_cached  # a page reads dozens of settings; the memo lives for one request and any write clears it
def raw_setting(db: Database, key: str):
    """The stored value of a setting, or None when it was never saved."""
    return db.scalar("SELECT value FROM settings WHERE key = ?", (key,))


class SettingsStore:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str) -> str:
        value = raw_setting(self.db, key)
        return DEFAULTS.get(key, "") if value is None else value

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES (?,?,?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now_iso()),
        )

    @property
    def base_currency(self) -> str:
        return self.get("base_currency")
