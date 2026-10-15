"""U4-U6: the account page's Money actions menu, Adjust balance, and the composition bar."""
import re
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from lightning.ui.web import create_app


@pytest.fixture
def client(c):
    return TestClient(create_app(c))


def _actions(html):
    return html[html.index('class="topbar') if 'class="topbar' in html else 0:]


def _money_menu(html):
    m = re.search(r'<details class="action-menu money-actions">.*?</details>', html, re.S)
    return m.group(0) if m else ""


def test_bank_and_cash_have_money_actions_with_exactly_three(client, setup):
    accounts, _ = setup
    for key in ("cib", "wallet"):
        menu = _money_menu(client.get(f"/accounts/{accounts[key].id}").text)
        assert menu.count("<a ") == 3
        assert "Convert currency" in menu and "Change ownership" in menu and "Bought in instalments" in menu


def test_brokerage_and_cd_have_no_money_actions(client, c, setup):
    accounts, _ = setup
    for key in ("thndr", "cd"):
        html = client.get(f"/accounts/{accounts[key].id}").text
        assert not _money_menu(html)
        assert "/convert" not in html and "/plan/purchases/new" not in html
    thndr = client.get(f"/accounts/{accounts['thndr'].id}").text
    assert "Change ownership" in thndr and "Adjust balance" in thndr


def test_physical_account_has_no_money_actions(client, c):
    gold = c.account_flows.open_account("Gold box", "PHYSICAL_ASSET", "2026-09-01", "0")
    html = client.get(f"/accounts/{gold.id}").text
    assert not _money_menu(html) and "/convert" not in html and "/plan/purchases/new" not in html


def test_adjust_balance_replaces_check_against_bank(client, c, setup):
    accounts, _ = setup
    for path in ("/accounts/%d", "/accounts/%d/reconcile"):
        assert "Check against bank" not in client.get(path % accounts["thndr"].id).text
    page = client.get(f"/accounts/{accounts['thndr'].id}/reconcile").text
    assert "Adjust balance" in page
    assert "Update value" in client.get(f"/accounts/{accounts['cd'].id}").text


@pytest.fixture
def broker(c, setup):
    accounts, _ = setup
    c.transactions.record_transfer("2026-09-02", accounts["cib"].id, accounts["thndr"].id, "30000")
    stock = c.assets.create_investment("Commercial International Bank", "STOCK", "COMI")
    return accounts["thndr"], stock


def test_one_class_no_custody_shows_no_composition_card(client, broker):
    thndr, _ = broker
    assert "account-composition" not in client.get(f"/accounts/{thndr.id}").text


def test_two_classes_show_bar_and_legend(client, c, broker):
    thndr, stock = broker
    c.investments.buy_total("2026-09-10", thndr.id, stock.id, "10", "1000")
    c.assets.set_price(stock.id, "2026-09-30", "110")
    html = client.get(f"/accounts/{thndr.id}").text
    card = html[html.index("account-composition"):]
    assert card.count('class="comp-bar"') == 1 and card.count("<i ") >= 2
    assert "comp-legend" in card and "Stocks" in card and "Brokerage Cash" in card
    assert "comp-held" not in card.split("</section>")[0]
    assert "By asset class" not in html


def test_custody_adds_owned_held_bar(client, c, broker):
    thndr, stock = broker
    c.investments.buy_total("2026-09-10", thndr.id, stock.id, "10", "1000")
    c.assets.set_price(stock.id, "2026-09-30", "110")
    c.money_from_others.record("2026-09-12", "Dad", thndr.id, D("500"))
    html = client.get(f"/accounts/{thndr.id}").text
    card = html[html.index("account-composition"):].split("</section>")[0]
    assert "comp-bar thin" in card and "comp-held" in card and "comp-owned" in card
