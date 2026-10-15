"""Emergency liquidity context labels accessible, locked and unknown holdings separately."""
from decimal import Decimal
from types import SimpleNamespace


def _holding(asset, class_code, value, locked_until=None):
    return SimpleNamespace(asset=asset, class_code=class_code, value=value, locked_until=locked_until)


def test_context_keeps_free_cash_money_market_locked_and_unknown_separate():
    from lightning.planning.emergency_context import emergency_liquidity_context

    position = SimpleNamespace(
        free_cash=Decimal("55560"),
        classes=(
            SimpleNamespace(name="Money Market Fund", items=[
                _holding("MMF", "FUND.MONEY_MARKET", Decimal("3033"))]),
            SimpleNamespace(name="CDs / Time Deposits", items=[
                _holding("CIB Certificate", "DEPOSIT.CD", Decimal("100000"), "2027-08-01")]),
            SimpleNamespace(name="Stocks", items=[
                _holding("CIB shares", "STOCK", Decimal("14000")),
                _holding("Unpriced share", "STOCK", None)]),
        ),
    )

    context = emergency_liquidity_context(position)
    assert context["free_cash"] == Decimal("55560")
    assert context["within_days"] == [{"label": "Money Market Fund", "value": Decimal("3033"), "unvalued": 0}]
    assert context["locked"] == [{"label": "CIB Certificate", "value": Decimal("100000"), "until": "2027-08-01"}]
    assert context["unknown"] == [{"label": "Stocks", "value": Decimal("14000"), "unvalued": 1}]
    assert "total" not in context


def test_unclassified_unvalued_holding_has_no_invented_value_or_timing():
    from lightning.planning.emergency_context import emergency_liquidity_context

    position = SimpleNamespace(free_cash=None, classes=(SimpleNamespace(name="Other", items=[
        _holding("Unpriced item", "OTHER", None)]),))
    context = emergency_liquidity_context(position)

    assert context["free_cash"] is None
    assert context["unknown"] == [{"label": "Other", "value": None, "unvalued": 1}]
    assert context["within_days"] == [] and context["locked"] == []


def test_reserves_and_health_show_the_display_only_context(c, setup):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from types import SimpleNamespace

    from lightning.core.dates import today
    from lightning.core.money import fmt
    from lightning.ui.web import create_app

    c.reserves.set_emergency_fund("5000")
    position = c.position.at(today())
    classes = (
        SimpleNamespace(name="Money Market Fund", items=[
            _holding("Money Market Fund", "FUND.MONEY_MARKET", Decimal("3033"))]),
        SimpleNamespace(name="CDs / Time Deposits", items=[
            _holding("CIB Certificate", "DEPOSIT.CD", Decimal("100000"), "2027-08-01")]),
        SimpleNamespace(name="Stocks", items=[
            _holding("CIB shares", "STOCK", Decimal("14000"))]),
    )
    c.position.at = lambda as_of=None, *, match_payments=True: replace(position, classes=classes)
    browser = TestClient(create_app(c))

    reserves = browser.get("/plan/reserves").text
    health = browser.get("/financial-health").text
    assert "Could also use" in reserves and "Could also use" in health
    for page in (reserves, health):
        assert f"{fmt(position.free_cash, 0)}" in page
        assert "Money Market Fund" in page and "3,033" in page and "Accessible in days" in page
        assert "CIB Certificate" in page and "100,000" in page and "Locked until 2027-08-01" in page
        assert "Stocks" in page and "14,000" in page and "Access timing unknown" in page
