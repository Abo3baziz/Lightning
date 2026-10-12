# Locking a month checked against the bank

**Status:** proposal, 2026-10-05 · Claude, not built. Learned from Actual (`actualbudget/actual` at `6245a46`; Lightning at `5665786`). When built, move what holds into [Architecture](../ARCHITECTURE.md) and delete this file.

**They do better:** once a row is reconciled, nothing changes it by accident, not even an import.

**How they do it:** a reconciled row has `reconciled = 1`; matching skips updating it (`sync.ts` line 673); the screens ask before editing it.

**Lightning today:** `reconciliation.py` checks a balance (`check`, line 57) and can post an adjustment (`adjust`), but nothing stops a later edit of a checked month.

**What to change:**
1. Migration: `reconciled_through(account_id PRIMARY KEY, date)`.
2. When `check(...).matches` and the user confirms, store the date.
3. `TransactionService.update`, `void` and `delete_many` refuse a line on that account dated on or before it: "This month was checked against the bank. Unlock it first." Import rows on or before it are marked skipped.
4. One **Unlock** link on the account page clears it.

**Done when:** tests: edit, void, delete and import are refused on or before the date, allowed after it and after unlocking.
