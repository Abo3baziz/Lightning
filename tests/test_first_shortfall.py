from decimal import Decimal

from lightning.planning.domain import CashForecast, ForecastMonth


def _month(month: str, closing: str) -> ForecastMonth:
    zero = Decimal(0)
    return ForecastMonth(month, zero, zero, False, zero, zero, zero, Decimal(closing))


def test_the_first_month_that_ends_below_reserves_is_named():
    months = [_month("2026-11", "5000"), _month("2026-12", "-200"), _month("2027-01", "-900")]
    forecast = CashForecast("2026-10-15", Decimal(0), None, 3, None, False, Decimal(0), [], months, [])
    assert forecast.first_short_month.month == "2026-12"
    safe = CashForecast("2026-10-15", Decimal(0), None, 3, None, False, Decimal(0), [], months[:1], [])
    assert safe.first_short_month is None
