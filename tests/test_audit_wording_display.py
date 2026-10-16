"""Audit wording and display fixes (2026-10-16): late payments, cash months beside the emergency fund,
one heading per review decision, the neutral Planned link."""
from datetime import date
from decimal import Decimal

from lightning.ui.web import create_app
from lightning.workflows.review import ReviewInbox, grouped
from tests.screens import _ScreenClient, visible_text


def _overdue_bill(c, accounts):
    c.planning.create(kind="BILL", name="Landlord", amount="12000", frequency="MONTHLY", start_date="2026-12-20",
                      account_id=str(accounts["cib"].id))


def test_an_unpaid_bill_past_its_date_says_how_many_days_late(c, setup):
    accounts, _ = setup
    _overdue_bill(c, accounts)
    day = date(2026, 12, 31)
    payments = c.planning.all_payments(date(2027, 1, 30), day)
    late = next(p for p in payments if p.due_date == "2026-12-20")
    assert late.days_late(day) == 11 and late.days_late(date(2026, 12, 20)) == 0
    upcoming = next(p for p in payments if p.due_date == "2027-01-20")
    assert upcoming.days_late(day) == 0
    item = next(i for i in ReviewInbox(c).items(day) if i["label"] == "Bill due: Landlord")
    assert item["late_days"] == 11
    assert grouped([item])[0]["late_days"] == 11


def test_the_late_chip_shows_on_the_plan_and_the_review(c, setup):
    accounts, _ = setup
    _overdue_bill(c, accounts)
    browser = _ScreenClient(create_app(c), "http://testserver")
    plan = visible_text(browser.get("/plan").text)
    assert "Landlord 2026-12-20" in plan and "Late · 11 days" in plan
    assert plan.index("Landlord 2026-12-20") < plan.index("Landlord 2027-01-20")  # late first
    assert "Late · 11 days" in visible_text(browser.get("/review").text)


def test_months_in_cash_sit_beside_the_emergency_fund(c, setup):
    c.budgets.set_emergency_basis("income")
    c.settings.set("budget_manual_monthly_income", "10000")
    day = date(2026, 12, 31)
    cash = c.position.at(day, match_payments=False).cash_you_own
    months = c.health.cash_months(day)
    assert months == cash / Decimal("10000") and months > 1
    assert c.health.overview(day)["cash_months"] == months
    page = visible_text(_ScreenClient(create_app(c), "http://testserver").get("/financial-health").text)
    assert f"{months:.1f} months in cash you own" in page


def test_the_planned_link_is_neutral(c, setup):
    browser = _ScreenClient(create_app(c), "http://testserver")
    assert "Bill linked" not in browser.get("/activity").text
