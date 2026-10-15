"""A page asks for the same asset's price at a dozen month ends: it reads that asset once per request, gives the
same answers as asking date by date, and sees a new price at once."""
from lightning.core.memo import request_cache


def _count(c, fragment):
    reads = []
    original = c.db.all

    def counting(sql, *args, **kwargs):
        if fragment in sql:
            reads.append(sql)
        return original(sql, *args, **kwargs)
    c.db.all = counting
    return reads, lambda: setattr(c.db, "all", original)


def test_prices_are_read_once_per_asset_and_answer_by_date(c, setup):
    accounts, _ = setup
    comi = c.assets.create_investment("Commercial International Bank", "STOCK", "COMI")
    c.assets.set_price(comi.id, "2026-09-01", "80")
    c.assets.set_price(comi.id, "2026-09-10", "90")
    c.assets.set_price(comi.id, "2026-09-10", "95", source="ONLINE")  # same day: the typed price wins
    q = c.reporting.q
    plain = {day: q.latest_price(comi.id, day) for day in ("2026-08-31", "2026-09-05", "2026-09-10", "2026-09-30")}
    reads, restore = _count(c, "FROM price_history")
    try:
        with request_cache(c.db):
            cached = {day: q.latest_price(comi.id, day) for day in plain}
            assert len(reads) == 1  # four dates, one read
            c.assets.set_price(comi.id, "2026-09-20", "100")
            assert q.latest_price(comi.id, "2026-09-30")["price_e6"] == 100_000_000  # a write inside is seen
    finally:
        restore()
    assert cached == plain
    assert plain["2026-08-31"] is None and plain["2026-09-05"]["price_e6"] == 80_000_000
    assert plain["2026-09-10"]["price_e6"] == 90_000_000


def test_totals_are_read_once_per_period_and_a_write_is_seen(c, setup):
    accounts, cats = setup
    food = cats["EXP.PERSONAL.FOOD"]
    q = c.reporting.q
    plain = q.category_totals("2026-10-01", "2026-10-31")
    reads, restore = _count(c, "GROUP BY le.category_id, le.effect")
    try:
        with request_cache(c.db):
            first = q.category_totals("2026-10-01", "2026-10-31")
            again = q.category_totals("2026-10-01", "2026-10-31")
            assert len(reads) == 1 and first == again == plain
            c.transactions.record_outflow("2026-10-05", accounts["cib"].id, "100", food.id)
            after = q.category_totals("2026-10-01", "2026-10-31")
            assert len(reads) == 2 and after != plain  # a write inside the request clears the memo
            after.append({"changed": True})  # a caller editing its copy does not change the next answer
            assert {"changed": True} not in q.category_totals("2026-10-01", "2026-10-31")
    finally:
        restore()
