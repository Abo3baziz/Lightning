# -*- coding: utf-8 -*-
"""3AI: preference writes from /settings (language, theme, privacy mode) are never undoable.
Undo and redo span ledger rows only; the language a user just picked does not silently revert."""
from __future__ import annotations

from lightning.undo import user_action

TODAY = "2026-12-31"


def test_language_change_is_not_recorded_as_an_undoable_action(c):
    with user_action("Saved changes"):  # the label the RequestCache middleware gives /settings/* posts
        c.settings.set("locale", "ar")
        assert c.settings.get("locale") == "ar"
    assert c.undo.available()["undo"] is None


def test_money_action_still_reverts_and_language_stays(c):
    bank = c.account_flows.open_account('Bank', 'BANK', '2026-09-01', '100')  # outside any recorded action
    food = c.categories.get_by_code('EXP.PERSONAL.FOOD').id
    with user_action("Saved changes"):  # the label the RequestCache middleware gives /settings/* posts
        c.settings.set("locale", "ar")
    with user_action("Transaction changes"):  # the action the user presses Undo about afterwards
        c.transactions.record_outflow('2026-09-02', bank.id, '80', food)
    group = c.undo.available()["undo"]
    assert group is not None and group["label"] == "Transaction changes"
    assert c.reporting.account_balance(bank.id) == 20
    c.undo.replay(expected_id=group["id"])
    assert c.reporting.account_balance(bank.id) == 100  # the money action is undone
    assert c.settings.get("locale") == "ar"  # the language keeps its chosen value
    # Redo brings the expense back, and again never touches the language.
    c.undo.replay(redo=True, expected_id=group["id"])
    assert c.reporting.account_balance(bank.id) == 20
    assert c.settings.get("locale") == "ar"
