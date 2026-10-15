from __future__ import annotations

from decimal import Decimal

import pytest

from lightning.core.errors import ValidationError


def _set_up(c, *, count=3):
    account = c.account_flows.open_account("Daily account", "BANK", "2026-09-01", "50000")
    food = c.categories.get_by_code("EXP.PERSONAL.FOOD")
    reserve = c.reserves.create("Food reserve", "1000", category_id=food.id)
    c.reserves.allocate(reserve["id"], "500")
    transactions = [c.transactions.record_outflow("2026-10-01", account.id, "100", food.id)
                    for _ in range(count)]
    return account, food, reserve, transactions


def test_batched_suggestions_match_single_transaction_rules(c):
    _, _, reserve, transactions = _set_up(c)
    ids = [row.id for row in transactions]

    batch = c.reserves.suggested_reserves_for_transactions(ids)
    assert set(batch) == set(ids)
    for transaction_id in ids:
        assert batch[transaction_id] == c.reserves.suggested_reserves(transaction_id)
        assert batch[transaction_id] == [{"id": reserve["id"], "name": "Food reserve",
                                          "amount": Decimal("100"), "remaining_after": Decimal("400")}]


def test_batched_suggestions_use_only_remaining_reserve_and_expense_capacity(c):
    account, food, reserve, transactions = _set_up(c, count=2)
    first, second = transactions
    income = c.transactions.record_inflow("2026-10-01", account.id, "200",
                                          c.categories.get_by_code("EXP.WORK.SALARY").id)
    other = c.account_flows.open_account("Other account", "BANK", "2026-09-01", "0")
    transfer = c.transactions.record_transfer("2026-10-01", account.id, other.id, "50")

    suggestions = c.reserves.suggested_reserves_for_transactions([first.id, second.id, income.id, transfer.id])
    assert suggestions[first.id][0]["amount"] == Decimal("100")
    assert suggestions[second.id][0]["amount"] == Decimal("100")
    assert suggestions[income.id] == [] and suggestions[transfer.id] == []
    assert c.reserves.suggested_reserves(first.id) == suggestions[first.id]

    c.reserves.set_expense_link(reserve["id"], first.id, "75")
    after_link = c.reserves.suggested_reserves_for_transactions([first.id, second.id])
    assert after_link[first.id] == []  # existing links are edited directly, not suggested as new partial uses
    assert after_link[second.id][0]["amount"] == Decimal("100")


def test_batched_reserve_suggestions_have_constant_select_count(c):
    _, _, _, transactions = _set_up(c, count=80)
    statements = []
    c.db.conn.set_trace_callback(statements.append)
    try:
        suggestions = c.reserves.suggested_reserves_for_transactions([row.id for row in transactions])
    finally:
        c.db.conn.set_trace_callback(None)
    select_count = sum(sql.lstrip().upper().startswith(("SELECT", "WITH")) for sql in statements)
    assert len(suggestions) == 80
    assert select_count <= 2


def test_reserve_link_rechecks_capacity_after_suggestion_was_read(c):
    account, food, reserve, transactions = _set_up(c, count=1)
    txn = transactions[0]
    suggestion = c.reserves.suggested_reserves_for_transactions([txn.id])[txn.id][0]
    assert suggestion["amount"] == Decimal("100")

    c.reserves.allocate(reserve["id"], "50")
    with pytest.raises(ValidationError, match="Assign more cash"):
        c.reserves.set_expense_link(reserve["id"], txn.id, suggestion["amount"])
    assert c.reserves.links_for_transaction(txn.id) == []
