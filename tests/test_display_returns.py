"""The owner's return display policy uses real gain before 365 days, then XIRR."""
from decimal import Decimal as D

from lightning.investments.returns import display_return


def test_short_return_counts_partial_sale_and_income_against_all_purchases():
    flows = [("2026-09-01", D("-1000")), ("2026-09-10", D("600")),
             ("2026-09-15", D("50")), ("2026-09-30", D("550"))]
    shown = display_return(flows, "2026-09-30", D("9"))
    assert (shown.percent, shown.annualized, shown.days_held) == (D("20"), False, 29)


def test_annual_return_starts_at_365_days_and_missing_values_stay_missing():
    flows = [("2025-10-01", D("-1000")), ("2026-10-01", D("1100"))]
    assert not display_return(flows, "2026-09-30", D("0.1")).annualized
    shown = display_return(flows, "2026-10-01", D("0.1"))
    assert (shown.percent, shown.annualized, shown.days_held) == (D("10"), True, 365)
    assert display_return(flows, "2026-10-01", D("0.1"), valued=False).percent is None
    assert display_return([], "2026-10-01", None).percent is None
