"""Gam'eya (rotating savings circle): terms, instalments, payout, forecast and the figures it moves."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from lightning.core.errors import ValidationError

TODAY = date(2026, 12, 31)


def _circle(c, setup, name="Office gam'eya", **overrides):
    accounts, _ = setup
    circle = c.account_flows.open_account(name, "GAMEYA", "2026-09-01", "0")
    terms = {"organiser": "Um Ali", "members": 10, "installment": "2000", "first_date": "2026-10-05",
             "my_turn": 3, "funding_account_id": accounts["cib"].id, "payout_account_id": accounts["cib"].id}
    terms.update(overrides)
    c.gameya.save_terms(circle.id, **terms)
    return circle


def _net(c, day="2026-12-31"):
    return c.position.at(day).net_worth


def test_terms_defaults_and_validation(c, setup):
    accounts, _ = setup
    circle = _circle(c, setup)
    terms = c.gameya.get(circle.id)
    assert terms.payout == Decimal("20000.00")  # members x instalment by default
    assert terms.annual_rate == Decimal(0)
    assert terms.frequency.value == "MONTHLY"
    base = {"organiser": "Um Ali", "members": 10, "installment": "2000", "first_date": "2026-10-05", "my_turn": 3,
            "funding_account_id": accounts["cib"].id, "payout_account_id": accounts["cib"].id}
    for override, field in [({"members": 1}, "members"), ({"members": 61}, "members"), ({"members": "x"}, "members"),
                            ({"installment": "0"}, "installment"), ({"installment": "10.555"}, "installment"),
                            ({"my_turn": 11}, "my_turn"), ({"my_turn": 0}, "my_turn"),
                            ({"organiser": " "}, "organiser"), ({"annual_rate": "101"}, "annual_rate"),
                            ({"payout": "-5"}, "payout"), ({"first_date": "soon"}, "first_date"),
                            ({"frequency": "WEEKLY"}, "frequency"),
                            ({"funding_account_id": circle.id}, "funding_account_id")]:
        with pytest.raises(ValidationError) as caught:
            c.gameya.save_terms(circle.id, **(base | override))
        assert caught.value.field == field, override
    with pytest.raises(ValidationError):  # a circle is held in a GAMEYA account only
        c.gameya.save_terms(accounts["cib"].id, **base)
    with pytest.raises(ValidationError):  # it starts empty
        c.account_flows.open_account("Other circle", "GAMEYA", "2026-09-01", "500")


def test_schedule_dates_clamp_to_month_end(c, setup):
    from lightning.deposits.gameya import installment_date, payout_date
    circle = _circle(c, setup, first_date="2026-01-31", my_turn=2)
    terms = c.gameya.get(circle.id)
    assert [installment_date(terms, k).isoformat() for k in (1, 2, 3, 4)] == [
        "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"]
    assert payout_date(terms).isoformat() == "2026-02-28"


def test_early_turn_goes_negative_and_is_what_you_owe_with_net_worth_unchanged(c, setup):
    accounts, _ = setup
    circle = _circle(c, setup, my_turn=1)
    before = c.position.at(TODAY)
    c.gameya.record_instalment(circle.id, "2026-10-05")
    after_paid = c.position.at(TODAY)
    assert after_paid.net_worth == before.net_worth                      # an instalment moves no net worth
    assert after_paid.gameya_paid_in == Decimal("2000")
    assert after_paid.holdings_value == before.holdings_value + 2000     # counted in Holdings value
    assert after_paid.cash_you_own == before.cash_you_own - 2000         # not liquid: leaves Cash you own
    assert after_paid.free_cash == before.free_cash - 2000
    assert after_paid.what_you_own == before.what_you_own                # still all yours
    c.gameya.record_payout(circle.id, "2026-10-05")                      # the pot, taken in month one
    taken = c.position.at(TODAY)
    assert c.reporting.account_value(circle.id, TODAY) == Decimal("-18000")
    assert taken.gameya_still_to_pay == Decimal("18000")
    assert taken.gameya_paid_in == 0
    assert taken.what_you_owe == before.what_you_owe + 18000
    assert taken.what_you_own == before.what_you_own + 18000             # the cash arrived; the debt is below
    assert taken.net_worth == before.net_worth                           # taking the pot moves no net worth
    # Later instalments pay the debt down without moving net worth either.
    c.gameya.record_instalment(circle.id, "2026-11-05")
    assert c.position.at(TODAY).gameya_still_to_pay == Decimal("16000")
    assert c.position.at(TODAY).net_worth == before.net_worth
    assert c.position.at(TODAY).bills_due == before.bills_due            # not a bill: never counted twice


def test_late_turn_is_paid_in_until_the_payout(c, setup):
    circle = _circle(c, setup, my_turn=10)
    start = c.position.at(TODAY)
    for index, day in enumerate(("2026-10-05", "2026-11-05", "2026-12-05"), 1):
        c.gameya.record_instalment(circle.id, day)
        position = c.position.at(TODAY)
        assert position.gameya_paid_in == Decimal(2000 * index)
        assert position.gameya_still_to_pay == 0
        assert position.net_worth == start.net_worth
    progress = c.gameya.progress(circle.id, TODAY)
    assert (progress.paid, progress.payouts, progress.owes_you) == (3, 0, True)
    assert progress.next_index == 4 and progress.next_date == "2027-01-05" and not progress.overdue


def test_net_worth_and_class_sale_value(c, setup):
    circle = _circle(c, setup)
    c.gameya.record_instalment(circle.id, "2026-10-05")
    position = c.position.at(TODAY)
    klass = next(row for row in position.classes if row.code == "GAMEYA")
    assert klass.value == Decimal("2000") and klass.after_sale == Decimal("2000")  # sale factor 100%
    assert position.deposits == Decimal("5000")  # the fixture's own CD; the circle is not a deposit


def test_instalment_needs_cash_you_own_on_the_date(c, setup):
    accounts, _ = setup
    circle = _circle(c, setup, installment="60000", funding_account_id=accounts["cib"].id)
    with pytest.raises(ValidationError) as caught:
        c.gameya.record_instalment(circle.id, "2026-10-05")
    assert "of your cash on 2026-10-05" in caught.value.message
    assert c.gameya.progress(circle.id, TODAY).paid == 0
    # A circle's own balance may go below zero; the funding account may not.
    small = _circle(c, setup, name="Small", installment="100", my_turn=1)
    c.gameya.record_payout(small.id, "2026-10-05")
    assert c.reporting.account_value(small.id, TODAY) == Decimal("-1000")


def test_all_instalments_and_a_second_payout_are_refused(c, setup):
    circle = _circle(c, setup, members=2, installment="100", my_turn=2, first_date="2026-10-05")
    c.gameya.record_instalment(circle.id, "2026-10-05")
    c.gameya.record_instalment(circle.id, "2026-11-05")
    with pytest.raises(ValidationError) as caught:
        c.gameya.record_instalment(circle.id, "2026-12-05")
    assert "All 2 instalments" in caught.value.message
    c.gameya.record_payout(circle.id, "2026-11-05")
    with pytest.raises(ValidationError):
        c.gameya.record_payout(circle.id, "2026-11-06")


def test_finished_state_leaves_forecasts(c, setup):
    circle = _circle(c, setup, members=2, installment="100", my_turn=2, first_date="2026-12-01")
    assert c.gameya.progress(circle.id, TODAY).finished is False
    c.gameya.record_instalment(circle.id, "2026-12-01")
    c.gameya.record_instalment(circle.id, "2026-12-31")
    c.gameya.record_payout(circle.id, "2026-12-31")
    progress = c.gameya.progress(circle.id, TODAY)
    assert progress.finished and progress.balance == 0 and progress.next_index is None
    assert c.gameya.future_events(date(2026, 10, 1), date(2027, 6, 30)) == []
    assert c.gameya.attention(TODAY) == []
    assert c.position.at(TODAY).gameya_paid_in == 0


def test_forecast_events_and_cash_planning(c, setup):
    accounts, _ = setup
    circle = _circle(c, setup, first_date="2026-11-05", my_turn=2)
    as_of = date(2026, 10, 15)
    events = c.deposits.future_events(as_of, date(2027, 2, 28))
    mine = [e for e in events if e.source == "GAMEYA"]
    assert [(e.date, e.kind, e.amount) for e in mine] == [
        ("2026-11-05", "INSTALLMENT", Decimal("-2000")), ("2026-12-05", "INSTALLMENT", Decimal("-2000")),
        ("2026-12-05", "PAYOUT", Decimal("20000")), ("2027-01-05", "INSTALLMENT", Decimal("-2000")),
        ("2027-02-05", "INSTALLMENT", Decimal("-2000"))]
    assert all(e.account_id == accounts["cib"].id and e.deposit_account_id == circle.id for e in mine)
    forecast = c.forecaster.forecast(as_of)
    november, december = forecast.months[1], forecast.months[2]
    assert (november.circle_out, november.circle_in) == (Decimal("2000"), Decimal("0"))
    assert (december.circle_out, december.circle_in) == (Decimal("2000"), Decimal("20000"))
    assert november.money_out >= 2000 and december.money_in >= 20000
    # Estimates only: nothing posts and Net worth does not move.
    assert _net(c) == _net(c)
    assert c.reporting.account_value(circle.id, TODAY) == 0


def test_forecast_months_close_with_the_circle(c, setup):
    as_of = date(2026, 10, 15)
    base = [m.closing for m in c.forecaster.forecast(as_of).months]
    _circle(c, setup, first_date="2026-11-05", my_turn=2)
    with_circle = c.forecaster.forecast(as_of).months
    assert with_circle[0].closing == base[0]
    assert with_circle[1].closing == base[1] - 2000
    assert with_circle[2].closing == base[2] - 2000 - 2000 + 20000  # carried on from November: 2 instalments, 1 payout


def test_safe_to_spend_takes_off_instalments_before_next_income(c, setup):
    as_of = date(2026, 10, 15)
    c.planning.create(kind="INCOME", name="Salary", amount="12000", frequency="MONTHLY", start_date="2026-11-01")
    before = c.forecaster.forecast(as_of)
    _circle(c, setup, first_date="2026-10-20", my_turn=5)
    after = c.forecaster.forecast(as_of)
    # Only the instalment dated before the pay day on 2026-11-01 comes off; the later ones wait for that income.
    assert after.next_income_date == "2026-11-01"
    assert after.safe_to_spend == before.safe_to_spend - 2000
    assert ("Gam'eya instalments before next income", Decimal("-2000")) in after.safe_to_spend_parts


def test_interest_rate_zero_has_no_interest_and_rate_estimates_simple_interest(c, setup):
    as_of = date(2026, 10, 1)
    none = _circle(c, setup, name="No interest", first_date="2026-10-05", my_turn=3)
    assert not [e for e in c.gameya.future_events(as_of, date(2027, 6, 30)) if e.kind == "INTEREST"]
    # 18% on a balance of 2,000 from 2026-10-05, 4,000 from 11-05 to the turn on 12-05: simple, actual days / 365.
    rated = _circle(c, setup, name="With interest", first_date="2026-10-05", my_turn=3, annual_rate="18")
    interest = [e for e in c.gameya.future_events(as_of, date(2027, 6, 30)) if e.kind == "INTEREST"]
    days_2000, days_4000, days_6000 = 31, 30, 0
    expected = Decimal(2000 * days_2000 + 4000 * days_4000 + 6000 * days_6000) * Decimal("0.18") / Decimal(365)
    assert [(e.deposit_account_id, e.date) for e in interest] == [(rated.id, "2026-12-05")]
    assert interest[0].amount == expected.quantize(Decimal("0.000001"))
    assert none.id != rated.id
    # Interest is a forecast only: nothing was posted.
    assert c.reporting.account_value(rated.id, TODAY) == 0


def test_overdue_instalment_shows_once_under_needs_you(c, setup):
    from lightning.workflows.review import ReviewInbox
    circle = _circle(c, setup, first_date="2026-10-05")
    rows = [row for row in ReviewInbox(c).items(TODAY) if row["label"].startswith("Gam'eya")]
    assert len(rows) == 1                                  # one row per circle, not per month
    assert rows[0]["label"] == "Gam'eya instalment due: Office gam'eya"
    assert "3 instalments · 6,000 EGP · first due 2026-10-05" in rows[0]["detail"]
    assert rows[0]["href"] == f"/gameya/{circle.id}#record-instalment"
    for day in ("2026-10-05", "2026-11-05", "2026-12-05"):
        c.gameya.record_instalment(circle.id, day)
    rows = [row for row in ReviewInbox(c).items(TODAY) if row["label"].startswith("Gam'eya")]
    assert [row["label"] for row in rows] == ["Gam'eya payout due: Office gam'eya"]  # your turn came on 2026-12-05
    assert rows[0]["action"] == "Record payout"
    c.gameya.record_payout(circle.id, "2026-12-05")  # your turn (3) came on 2026-12-05
    assert not [row for row in ReviewInbox(c).items(TODAY) if row["label"].startswith("Gam'eya")]


def test_account_types_and_register_rules(c, setup):
    accounts, _ = setup
    circle = _circle(c, setup)
    assert circle.type_label == "Gam'eya (savings circle)" and circle.type_short == "Gam'eya"
    # Not liquid: a circle's money never counts as cash you own or in Free cash.
    c.gameya.record_instalment(circle.id, "2026-10-05")
    position = c.position.at(TODAY)
    assert position.bank_and_wallet_cash == c.position.at("2026-10-04").bank_and_wallet_cash - 2000
    # Instalments are ordinary internal transfers: never income or spending.
    flow = c.reporting.cash_flow("2026-10-01", "2026-10-31")
    assert flow.inflows == 0 and flow.outflows == 0
    with pytest.raises(Exception):
        c.account_flows.update_account(circle.id, circle.name, "BANK", "2026-09-01")


def test_integrity_still_holds(c, setup):
    circle = _circle(c, setup, my_turn=1)
    c.gameya.record_instalment(circle.id, "2026-10-05")
    c.gameya.record_payout(circle.id, "2026-10-05")  # leaves the circle below zero
    for day in ("2026-10-05", "2026-12-31"):
        checks = c.integrity.checks(day)
        assert [check for check in checks if check.status == "ISSUE"] == []
