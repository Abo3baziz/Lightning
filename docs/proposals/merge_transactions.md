# Merging two transactions

**Status:** proposal, 2026-10-05 · Claude, not built. Learned from Actual (`actualbudget/actual` at `6245a46`; Lightning at `5665786`). When built, move what holds into [Architecture](../ARCHITECTURE.md) and delete this file.

**They do better:** two rows that are the same payment become one, keeping the best of each.

**How they do it** (`loot-core/src/server/transactions/merge.ts`):
1. Keep the row with the bank id.
2. Copy payee, category and notes from the other row where the kept row is empty.
3. Delete the other row; a transfer stays linked.

**Lightning today:** none; the user voids one by hand and loses its category or notes.

**What to change:** `TransactionService.merge(keep_id, drop_id)` in one transaction (one undo step with [undo](undo.md)): refuse if amounts or accounts differ; keep the one with `bank_reference`; copy category, notes, tags and counterparty where empty; void the other with reason "Merged into REF". A "Merge" action when exactly two rows are selected in the register.

**Done when:** a test merges a typed and an imported row and the kept row has the bank reference and the typed category.

---

## 2. GnuCash
