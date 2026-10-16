"""Investment events: a dividend with tax withheld, a broker fee, interest on broker cash, and moving
shares between brokers. Net-only dividends stay the simple default."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from lightning.core.errors import ValidationError
from lightning.investments.report import investment_period
from lightning.ui.web import create_app

D = Decimal
START, END = "2026-09-01", "2026-12-31"


@pytest.fixture
def inv(c, setup):
    accounts, _ = setup
    thndr = accounts["thndr"]
    second = c.account_flows.open_account("Second Broker", "BROKERAGE", "2026-09-01", "0", institution="Other")
    c.transactions.record_transfer("2026-09-02", accounts["cib"].id, thndr.id, "30000")
    comi = c.assets.create_investment("Commercial International Bank", "STOCK", "COMI")
    c.investments.buy("2026-09-03", thndr.id, comi.id, "100", "50")  # 5,000
    return c, thndr, second, comi


def report(c):
    return investment_period(c.db, c.accounts, c.assets, c.reporting, START, END)


def position(c, account, asset, day=END):
    return next(p for p in c.investments.portfolio(day, account.id).positions if p.asset_id == asset.id)


def cash(c, account, day=END):
    return c.reporting.account_balance(account.id, day)


def test_net_only_dividend_is_unchanged(inv):
    c, thndr, _, comi = inv
    before = cash(c, thndr)
    txn = c.investments.dividend("2026-10-01", thndr.id, comi.id, "200")
    assert len(txn.lines) == 1 and txn.lines[0].quantity == D("200")
    assert cash(c, thndr) == before + 200
    r = report(c)
    assert (r["dividends"], r["tax"], r["fees"]) == (D("200"), 0, 0)
    assert position(c, thndr, comi).dividend_tax == 0


def test_dividend_with_tax_posts_gross_tax_and_net(inv):
    c, thndr, _, comi = inv
    before = cash(c, thndr)
    base = report(c)["result"]
    txn = c.investments.dividend("2026-10-01", thndr.id, comi.id, "200", tax="20")
    assert sorted(line.quantity for line in txn.lines) == [D("-20"), D("200")]
    assert cash(c, thndr) == before + 180  # the net lands in cash
    assert c.db.scalar("SELECT asset_id FROM investment_dividend_assets WHERE transaction_id=?", (txn.id,)) == comi.id
    r = report(c)
    assert r["dividends"] == D("200") and r["tax"] == D("20")  # income is gross
    assert r["result"] - base == D("180")  # Net gain uses net
    p = position(c, thndr, comi)
    assert (p.dividends, p.dividend_tax, p.net_dividends) == (D("200"), D("20"), D("180"))
    assert p.total_return == (p.unrealized or 0) + D("180")
    # Tax is an investment cost: no household spending, no budget line
    flow = c.reporting.cash_flow(START, END)
    assert flow.personal_outflows == c.reporting.cash_flow(START, "2026-09-30").personal_outflows
    assert flow.investment_outflows >= D("20")
    assert c.categories.get_by_code("EXP.INVEST.TAX").family.value == "INVESTMENT"
    # Money added ignores the tax
    assert report(c)["net_money"] == base_money(c)


def base_money(c):
    return investment_period(c.db, c.accounts, c.assets, c.reporting, START, "2026-09-30")["net_money"]


def test_dividend_tax_must_be_less_than_the_dividend(inv):
    c, thndr, _, comi = inv
    with pytest.raises(ValidationError):
        c.investments.dividend("2026-10-01", thndr.id, comi.id, "200", tax="200")
    with pytest.raises(ValidationError):
        c.investments.dividend("2026-10-01", thndr.id, comi.id, "200", tax="-1")


def test_editing_a_taxed_dividend_keeps_the_tax(inv):
    c, thndr, _, comi = inv
    txn = c.investments.dividend("2026-10-01", thndr.id, comi.id, "200", tax="20")
    values = c.investments.values_of(txn.id)
    assert values["amount"] == D("200") and values["tax"] == D("20")
    c.investments.update(txn.id, account_id=thndr.id, asset_id=comi.id, amount="300", date="2026-10-01")
    r = report(c)
    assert (r["dividends"], r["tax"]) == (D("300"), D("20"))


def test_broker_fee_lowers_net_gain_and_is_not_spending(inv):
    c, thndr, _, comi = inv
    before_cash, base = cash(c, thndr), report(c)
    flow_before = c.reporting.cash_flow(START, END)
    c.investments.broker_fee("2026-10-05", thndr.id, "35")
    assert cash(c, thndr) == before_cash - 35
    r = report(c)
    assert r["fees"] == D("35") and r["result"] == base["result"] - 35
    assert r["net_money"] == base["net_money"]  # a cost, not money taken out
    flow = c.reporting.cash_flow(START, END)
    assert flow.personal_outflows == flow_before.personal_outflows
    assert flow.work_outflows == flow_before.work_outflows
    code = c.db.scalar("SELECT c.code FROM ledger_entries le JOIN categories c ON c.id=le.category_id "
                       "JOIN transactions t ON t.id=le.transaction_id WHERE t.date='2026-10-05'")
    assert code == "EXP.INVEST.FEES"
    assert c.categories.get_by_code(code).family.value == "INVESTMENT"
    with pytest.raises(ValidationError):
        c.investments.broker_fee("2026-10-05", thndr.id, "0")


def test_fee_and_interest_need_a_brokerage_account(inv, setup):
    c, *_ = inv
    accounts, _ = setup
    with pytest.raises(ValidationError):
        c.investments.broker_fee("2026-10-05", accounts["cib"].id, "5")
    with pytest.raises(ValidationError):
        c.investments.broker_interest("2026-10-05", accounts["cib"].id, "5")


def test_interest_on_broker_cash_counts_as_dividends_and_interest(inv):
    c, thndr, _, comi = inv
    before_cash, base = cash(c, thndr), report(c)
    c.investments.broker_interest("2026-10-06", thndr.id, "12.50")
    assert cash(c, thndr) == before_cash + D("12.50")
    r = report(c)
    assert r["dividends"] == base["dividends"] + D("12.50")
    assert r["result"] == base["result"] + D("12.50")
    assert r["net_money"] == base["net_money"]


def test_move_keeps_units_cost_and_net_gain(inv):
    c, thndr, second, comi = inv
    c.assets.set_price(comi.id, "2026-12-30", "60")
    c.investments.buy("2026-09-10", thndr.id, comi.id, "100", "70")  # average cost 60
    before = report(c)
    cost_before = position(c, thndr, comi).cost_basis
    cash_before = (cash(c, thndr), cash(c, second))
    txn = c.investments.move_units("2026-10-10", thndr.id, second.id, comi.id, "50")
    assert txn.type.value == "TRF" and len(txn.lines) == 2
    assert sum(line.amount_base for line in txn.lines) == 0
    assert (cash(c, thndr), cash(c, second)) == cash_before  # no cash moves
    src, dst = position(c, thndr, comi), position(c, second, comi)
    assert (src.quantity, dst.quantity) == (D("150"), D("50"))
    assert src.cost_basis + dst.cost_basis == cost_before
    assert dst.average_cost == src.average_cost == D("60")
    after = report(c)
    assert after["result"] == before["result"] and after["net_money"] == before["net_money"]
    assert after["realized"] == before["realized"]
    stock = {h["account"]: h["units"] for h in after["holdings"] if h.get("asset_id") == comi.id}
    assert stock == {thndr.label: D("150"), second.label: D("50")}
    assert sum(h["cost"] for h in after["holdings"]) == sum(h["cost"] for h in before["holdings"])
    # Everything can go; the source then holds nothing
    c.investments.move_units("2026-10-11", thndr.id, second.id, comi.id, "150")
    assert position(c, second, comi).quantity == D("200")
    assert not position(c, thndr, comi).is_open


def test_move_is_refused_when_it_cannot_be_right(inv, setup):
    c, thndr, second, comi = inv
    accounts, _ = setup
    with pytest.raises(ValidationError):
        c.investments.move_units("2026-10-10", thndr.id, second.id, comi.id, "101")  # holds 100
    with pytest.raises(ValidationError):
        c.investments.move_units("2026-10-10", thndr.id, thndr.id, comi.id, "1")
    with pytest.raises(ValidationError):
        c.investments.move_units("2026-10-10", thndr.id, accounts["cib"].id, comi.id, "1")  # not a broker
    c.currencies.register("USD")
    usd = c.account_flows.open_account("US Broker", "BROKERAGE", "2026-09-01", "0", currency="USD")
    with pytest.raises(ValidationError):
        c.investments.move_units("2026-10-10", thndr.id, usd.id, comi.id, "1")
    assert position(c, thndr, comi).quantity == D("100")


def test_entry_form_posts_each_event(inv):
    c, thndr, second, comi = inv
    client = TestClient(create_app(c), follow_redirects=False)
    page = client.get(f"/accounts/{thndr.id}")
    assert 'data-trade-action="fee"' in page.text and 'data-trade-action="move"' in page.text
    assert 'name="tax_withheld"' in page.text and second.label in page.text
    url = f"/accounts/{thndr.id}/investment-entry"
    key = f"asset:{comi.id}"

    net = client.post(url, data={"date": "2026-10-01", "instrument_key": key, "trade_action": "dividend",
                                 "total": "100"})
    assert net.status_code == 303 and report(c)["tax"] == 0
    taxed = client.post(url, data={"date": "2026-10-02", "instrument_key": key, "trade_action": "dividend",
                                   "total": "200", "tax_withheld": "20"})
    assert taxed.status_code == 303
    r = report(c)
    assert (r["dividends"], r["tax"]) == (D("300"), D("20"))

    fee = client.post(url, data={"date": "2026-10-03", "trade_action": "fee", "total": "15"})
    assert fee.status_code == 303 and report(c)["fees"] == D("15")
    interest = client.post(url, data={"date": "2026-10-04", "trade_action": "interest", "total": "8"})
    assert interest.status_code == 303 and report(c)["dividends"] == D("308")

    too_many = client.post(url, data={"date": "2026-10-05", "instrument_key": key, "trade_action": "move",
                                      "units": "500", "to_account_id": str(second.id)})
    assert too_many.status_code == 400
    no_target = client.post(url, data={"date": "2026-10-05", "instrument_key": key, "trade_action": "move",
                                       "units": "10"})
    assert no_target.status_code == 400
    moved = client.post(url, data={"date": "2026-10-05", "instrument_key": key, "trade_action": "move",
                                   "units": "40", "to_account_id": str(second.id)})
    assert moved.status_code == 303
    assert (position(c, thndr, comi).quantity, position(c, second, comi).quantity) == (D("60"), D("40"))
    assert client.get(f"/accounts/{second.id}").status_code == 200
    assert client.get(f"/investments/holding/{comi.id}?account={second.id}").status_code == 200
    assert client.get("/investments").status_code == 200
    assert client.get(f"/accounts/{thndr.id}").status_code == 200
