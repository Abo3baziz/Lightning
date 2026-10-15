from __future__ import annotations

import pytest

from lightning.core.errors import ValidationError
from lightning.undo import user_action


def test_transaction_action_undoes_and_redoes_cascade_rows(c, setup):
    accounts, cats = setup
    account_id = accounts["cib"].id
    before = c.reporting.account_balance(account_id)

    with user_action("Record groceries"):
        txn = c.transactions.record_outflow("2026-10-02", account_id, "85", cats["EXP.PERSONAL.FOOD"].id)

    group = c.undo.available()["undo"]
    assert group and group["label"] == "Record groceries"
    after = c.reporting.account_balance(account_id)
    assert after == before - 85
    c.undo.replay(expected_id=group["id"])
    assert c.db.scalar("SELECT 1 FROM transactions WHERE id=?", (txn.id,)) is None
    assert c.db.scalar("SELECT 1 FROM ledger_entries WHERE transaction_id=?", (txn.id,)) is None
    assert c.reporting.account_balance(account_id) == before

    redo = c.undo.available()["redo"]
    assert redo and redo["id"] == group["id"]
    c.undo.replay(redo=True, expected_id=redo["id"])
    assert c.db.scalar("SELECT status FROM transactions WHERE id=?", (txn.id,)) == "POSTED"
    assert c.reporting.account_balance(account_id) == after


def test_stale_action_replay_refuses_external_edit_without_partial_undo(c, setup):
    accounts, cats = setup
    account_id = accounts["cib"].id
    with user_action("Record groceries"):
        txn = c.transactions.record_outflow("2026-10-02", account_id, "85", cats["EXP.PERSONAL.FOOD"].id)
    group = c.undo.available()["undo"]
    c.db.execute("UPDATE transactions SET notes='changed outside history' WHERE id=?", (txn.id,))

    with pytest.raises(ValidationError, match="changed since it was saved"):
        c.undo.replay(expected_id=group["id"])
    assert c.db.scalar("SELECT status FROM transactions WHERE id=?", (txn.id,)) == "POSTED"
    assert c.reporting.account_balance(account_id) < 50_000


def test_checked_history_guards_changes_and_unlock_can_be_undone(c, setup):
    accounts, cats = setup
    account_id = accounts["cib"].id
    through = "2026-10-01"
    balance = c.reconciliation.balance(account_id, through)
    c.reconciliation.close(account_id, through, balance)
    assert c.reconciliation.checked_through(account_id) == through

    with pytest.raises(ValidationError, match="Unlock it first"):
        c.transactions.record_outflow(through, account_id, "20", cats["EXP.PERSONAL.FOOD"].id)

    c.reconciliation.unlock(account_id)
    assert c.reconciliation.checked_through(account_id) is None
    history = c.undo.available()["undo"]
    assert history and history["label"] == "Unlock account history"
    c.undo.replay(expected_id=history["id"])
    assert c.reconciliation.checked_through(account_id) == through


def test_duplicate_merge_preserves_metadata_effect_and_can_be_undone(c, setup):
    accounts, cats = setup
    account_id = accounts["cib"].id
    category_id = cats["EXP.PERSONAL.FOOD"].id
    keep = c.transactions.record_outflow("2026-10-03", account_id, "55", category_id)
    drop = c.transactions.record_outflow("2026-10-04", account_id, "55", category_id,
                                         counterparty="Market", notes="receipt #groceries")
    balance_before = c.reporting.account_balance(account_id)
    preview = c.transactions.merge_preview(keep.id, drop.id)

    merged = c.transactions.merge(keep.id, drop.id, preview.fingerprint)
    assert merged.id == keep.id
    assert merged.counterparty == "Market" and "receipt" in merged.notes and "#groceries" in merged.notes
    assert c.db.scalar("SELECT category_id FROM ledger_entries WHERE transaction_id=?", (keep.id,)) == category_id
    assert c.db.scalar("SELECT status FROM transactions WHERE id=?", (drop.id,)) == "VOID"
    assert c.reporting.account_balance(account_id) == balance_before + 55

    group = c.undo.available()["undo"]
    assert group and group["label"] == "Merge duplicate transactions"
    c.undo.replay(expected_id=group["id"])
    assert c.db.scalar("SELECT status FROM transactions WHERE id=?", (drop.id,)) == "POSTED"
    restored = c.transactions.get(keep.id)
    assert restored.counterparty == "" and restored.notes == ""
    assert c.reporting.account_balance(account_id) == balance_before
