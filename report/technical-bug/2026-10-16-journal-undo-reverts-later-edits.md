---
title: Journal undo silently reverts later edits made on other devices
category: technical-bug
area: journal
status: reported
created: 2026-10-16
reporter: Claude
skills: none
app_version: 1.1.0b1
commit: 34f0e5a
repo: app
---

## Report

`JournalDevice.undo` (`lightning/sync/journal/device.py`, `undo`) restores the record's **whole** earlier group set and signs it with the record's **current** tokens as bases. A later change to any group therefore never conflicts: it is overwritten without review. This breaks G4 (no silent conflicting overwrite) and the proposal's rule that undo "can itself conflict".

Reproduce (three encrypted dummy devices, as in `tests/test_journal_finance.py`):
1. PC A adds a 10.00 expense (Food). Sync.
2. PC A edits the amount to 25.00. Sync. Call this edit *U*.
3. Phone B changes the category to another expense category. Sync.
4. PC A undoes *U*, then syncs.

Result: every decision is `accepted`; the amount is back to 10.00 **and B's category change is gone** with no review. If B had changed the amount instead, B's amount would be lost the same way: wrong money.

`JournalCapture.undo_batch` uses the same path, so undoing an import deletes payments that were edited after the import without review (the proposal's table says such a delete goes to review).

Severity: high (silent loss of another device's confirmed edit, possibly money).

Expected: undo sends only the groups the undone action changed, with that action's resulting tokens as bases, so a later change to the same group goes to review. Undo of an add (delete) uses the add's tokens as bases.
