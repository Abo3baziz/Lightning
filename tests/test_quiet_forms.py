"""U3 layout, U8, U9 display, U12, U13: quiet forms with fewer words."""
import pytest
from fastapi.testclient import TestClient

from lightning.ui import routes
from lightning.ui.routes import register
from lightning.ui.web import create_app


@pytest.fixture
def client(c):
    return TestClient(create_app(c))


@pytest.fixture
def thndr(c, setup):
    accounts, _ = setup
    return accounts["thndr"]


def test_investment_form_has_no_removed_sentences_and_no_tone_buttons(client, thndr):
    html = client.get(f"/accounts/{thndr.id}").text
    form = html[html.index("investment-entry-card"):html.index("trade-instrument-catalogue")]
    for gone in ("Choose Buy, Sell, or Dividend", "Leave fees at 0", "Enter the number of units bought",
                 "Choose an instrument from the results", "Held for someone else", "Fees inside the amount"):
        assert gone not in form
    assert 'class="investment-segment"' in form and "action-sell" not in form and "action-dividend" not in form
    assert "rose" not in form and "azure" not in form
    assert 'id="investment-pay-line"' in form and 'name="whom"' in form
    assert form.count("Add investment transaction") == 1
    assert "Add fees on top instead" in form  # the fee choice stays until the fee rule changes


def test_picker_results_are_one_line_with_exchange_and_no_type_word():
    js = open("lightning/ui/static/app.js", encoding="utf-8").read()
    assert "${item.kind} · ${item.ticker}" not in js
    assert "${item.ticker}${item.exchange ? ` · ${item.exchange}` : \"\"}" in js
    css = open("lightning/ui/static/style.css", encoding="utf-8").read()
    assert ".instrument-results { position: absolute;" in css


def test_same_ticker_on_two_exchanges_stays_two_pickable_holdings(c, thndr, monkeypatch):
    rows = [{"ticker": "ABC", "name": "Alpha Corp", "class_code": "STOCK", "mic": "XCAI", "currency": "EGP"},
            {"ticker": "ABC", "name": "Alpha Corp ADR", "class_code": "STOCK", "mic": "XNYS", "currency": "USD"}]
    monkeypatch.setattr(register, "catalog_instruments", lambda: rows)
    choices = [ch for ch in register._trade_choices(c, thndr, []) if ch["ticker"] == "ABC"]
    assert len(choices) == 2 and len({ch["key"] for ch in choices}) == 2
    assert {ch["exchange"] for ch in choices} == {"EGX", "NYSE"}
    a = c.assets.create_investment("Alpha Corp", "STOCK", "ABC", mic="XCAI")
    b = c.assets.create_investment("Alpha Corp ADR", "STOCK", "ABC", mic="XNYS")
    assert a.id != b.id and a.code != b.code
    after = {ch["exchange"]: ch["key"] for ch in register._trade_choices(c, thndr, []) if ch["ticker"] == "ABC"}
    assert after == {"EGX": f"asset:{a.id}", "NYSE": f"asset:{b.id}"}


def test_salary_setup_asks_when_it_arrives(client, setup):
    html = client.get("/setup/salary").text
    assert "Salary arrives on" in html and "of each month" in html and "Lightning expects it then" in html
    assert ">Payday<" not in html


def test_recurring_item_form_is_compact_and_hides_unused_schedule_fields(client):
    html = client.get("/plan/items/new?kind=BILL").text
    assert "form-grid" in html and "plan-form-compact" in html
    monthly_end = html[html.index('id="end_date"') - 120:html.index('id="end_date"')]
    assert "hidden" not in monthly_end
    once = client.get("/plan/items/new?kind=BILL&frequency=ONCE").text
    assert once.count("data-repeat-only hidden") == 2  # Every and Ends only show for a repeating schedule
    assert "data-repeat-only hidden" not in html
