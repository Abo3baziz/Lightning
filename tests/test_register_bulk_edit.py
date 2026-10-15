"""U2: edit many register rows at once; only the changed fields apply, amounts never do."""
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from lightning.ui.web import create_app


NAMES = ["Carrefour", "Vodafone", "Zamalek Club"]


@pytest.fixture
def client(c):
    return TestClient(create_app(c))


@pytest.fixture
def rows(c, setup):
    accounts, cats = setup
    cib = accounts["cib"]
    food = cats["EXP.PERSONAL.FOOD"]
    made = [c.transactions.record_in_account(cib.id, f"2026-09-1{n}", f"-{100 * n}", food.id, None, NAMES[n - 1], "")
            for n in (1, 2, 3)]
    return c, accounts, cats, made


def test_bulk_edit_changes_category_and_notes_and_leaves_amounts(rows):
    c, accounts, cats, made = rows
    software = cats["EXP.WORK.SOFTWARE"]
    changed, skipped = c.transactions.bulk_update([t.id for t in made], {"category_id": software.id, "notes": "team plan"})
    assert changed == [t.id for t in made] and skipped == []
    for n, t in enumerate(made, 1):
        now = c.transactions.get(t.id)
        assert now.notes == "team plan" and now.counterparty == NAMES[n - 1] and now.date == f"2026-09-1{n}"
        assert any(line.category_id == software.id for line in now.lines)
        cash = next(line for line in now.lines if c.assets.get_asset(line.asset_id).is_cash)
        assert cash.quantity == D(-100 * n)


def test_only_changed_fields_apply(rows):
    c, accounts, cats, made = rows
    c.transactions.bulk_update([t.id for t in made], {"notes": "only notes"})
    now = c.transactions.get(made[0].id)
    assert now.notes == "only notes" and now.counterparty == NAMES[0]
    assert any(line.category_id == cats["EXP.PERSONAL.FOOD"].id for line in now.lines)


def test_rows_that_cannot_take_the_change_are_skipped_and_counted(rows):
    c, accounts, cats, made = rows
    stock = c.assets.create_investment("Commercial International Bank", "STOCK", "COMI")
    c.transactions.record_transfer("2026-09-02", accounts["cib"].id, accounts["thndr"].id, "30000")
    buy = c.investments.buy_total("2026-09-10", accounts["thndr"].id, stock.id, "10", "1000")
    changed, skipped = c.transactions.bulk_update([made[0].id, buy.id], {"counterparty": "Somewhere"})
    assert changed == [made[0].id] and skipped == [buy.id]
    assert c.transactions.get(made[0].id).counterparty == "Somewhere"


def test_bulk_edit_route_flashes_and_applies(client, rows):
    c, accounts, cats, made = rows
    r = client.post("/transactions/bulk-edit", follow_redirects=False,
                    data={"txn_ids": [str(t.id) for t in made], "notes": "bulk", "category": "Software",
                          "category_choice": str(cats["EXP.WORK.SOFTWARE"].id), "back": "/accounts/%d" % accounts["cib"].id})
    assert r.status_code in (302, 303)
    assert all(c.transactions.get(t.id).notes == "bulk" for t in made)


def test_bulk_category_still_works(client, rows):
    c, accounts, cats, made = rows
    client.post("/transactions/bulk-category", follow_redirects=False,
                data={"txn_ids": [str(t.id) for t in made], "category_id": str(cats["EXP.WORK.SOFTWARE"].id)})
    assert all(any(l.category_id == cats["EXP.WORK.SOFTWARE"].id for l in c.transactions.get(t.id).lines) for t in made)


def test_edit_page_carries_original_values_for_the_dialog(client, rows):
    c, accounts, cats, made = rows
    html = client.get(f"/accounts/{accounts['cib'].id}?edit={made[0].id}&acct={accounts['cib'].id}").text
    assert "data-original='" in html and NAMES[0] in html
