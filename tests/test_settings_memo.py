"""A page reads dozens of settings: inside one request each is read once, and a write is seen at once."""
from lightning.core.memo import request_cache


def test_settings_are_read_once_per_request_and_writes_show_at_once(c):
    reads = []
    original = c.db.scalar

    def counting(sql, *args, **kwargs):
        if "FROM settings" in sql:
            reads.append(sql)
        return original(sql, *args, **kwargs)

    c.db.scalar = counting
    try:
        with request_cache(c.db):
            first = [c.settings.get("base_currency") for _ in range(5)]
            assert len(reads) == 1 and set(first) == {"EGP"}
            c.settings.set("budget_income_months", "6")
            assert c.budgets._average_months() == 6  # a write inside the request is read fresh
        reads.clear()
        c.settings.get("base_currency")
        c.settings.get("base_currency")
        assert len(reads) == 2  # outside a request nothing is remembered
    finally:
        c.db.scalar = original
