# Undo for edits, deletes and imports

**Status:** proposal, 2026-10-05 · Claude, not built. Learned from Actual (`actualbudget/actual` at `6245a46`; Lightning at `5665786`). When built, move what holds into [Architecture](../ARCHITECTURE.md) and delete this file.

**They do better:** any change can be undone, up to 20 steps back.

**How they do it** (`loot-core/src/server/undo.ts`):
1. Every write is a sync message that carries the **old value** (`appendMessages(messages, oldData)`).
2. `withUndo` puts a **marker** in the history; everything written until the next marker is one step.
3. Undo replays the old values of the last step; redo replays the new ones. 20 markers are kept (`HISTORY_SIZE`).
4. Screens wrap each user action in `undoable(...)`; background work does not.

**Lightning today:** no message layer. Every write goes through `Database.transaction()` (`database/connection.py` line 107). Undo exists only for the budget bulk rule (`ui/routes/budget.py` lines 665–698, a snapshot in a setting) and a skipped payment. A voided or deleted transaction can be restored, but an **edit or an import cannot be undone**.

**What to change:**
1. Migration: `undo_groups(id, label, created_at)` and `undo_log(group_id, seq, sql, params_json)`.
2. For each user-data table (transactions, ledger entries, budgets, planned items, categories, counterparties, rules), triggers `AFTER INSERT/UPDATE/DELETE` write the **inverse** statement into `undo_log`, under the current group read from a one-row `TEMP` table. With no current group they write nothing.
3. `Database.transaction(undo_label=None)`: at depth 0 with a label, open a group and set the temp row; clear it at commit or rollback. Migrations, price downloads and system revaluations pass no label, so they never enter the history.
4. `lightning/undo.py` `UndoService`: `undo()` runs the last group's inverse statements newest first in one transaction, then runs the integrity checks and refuses (rolls back) if one fails. Keep 20 groups. Clear the log when the profile closes and before a phone hand-off (the multi-device plan must not carry it).
5. Screens: the message after save, delete or import gets an **Undo** button. Move the budget bulk undo onto this service.
6. A test that lists every user-data table and fails if one lacks its three triggers.

**Done when:** tests undo an edit, a delete, an import of 30 rows and a bulk change, each leaving the database byte-for-byte equal in content to before; undo after a migration is refused. Mohab imports the wrong file and undoes it in one click.
