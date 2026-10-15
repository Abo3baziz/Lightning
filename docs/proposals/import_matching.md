# Finding the same transaction on import

**Status:** proposal, 2026-10-05 · Claude, not built. Learned from Actual (`actualbudget/actual` at `6245a46`; Lightning at `5665786`). When built, move what holds into [Architecture](../ARCHITECTURE.md) and delete this file. Owner decision: the import link window.

**They do better:** a payment the bank posts up to a week after the user typed it is still offered as the same transaction.

**How they do it** (`loot-core/src/server/accounts/sync.ts`, `matchTransactions`, line 826):
1. A row with the same bank id matches first.
2. Otherwise, candidates are rows in the same account with the **same amount within 7 days either side** (line 895).
3. Ranked by date distance, then rows **without** a bank id first, because those were typed by hand (`compareFuzzyMatchCandidates`, line 804).

**Lightning today:** already the same shape, with a narrower window: `bank_imports.py` `_link_candidates` offers entries with the same amount within `LINK_WINDOW_DAYS = 3`, closest first, never one already backed by an imported row, and never one entry to two rows ([Architecture › CSV import and export contract](../ARCHITECTURE.md)).

**What to change:** only `LINK_WINDOW_DAYS`, from 3 to 7, and the window test (`tests/test_bank_import_matching.py`, "within three days"). **The owner decides:** 7 catches slow card postings; but a weekly payment of the same amount (a café, a class) would then be offered last week's entry when this week's was not typed, and a row with a candidate defaults to *Link*. 3 avoids that.

**Done when:** the window test moves to the new number, and a test shows a weekly equal payment still posts as new when its own entry was not typed.
