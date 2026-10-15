---
title: Searching transactions for an amount finds nothing
category: technical-improvement
area: transactions
status: open
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: none
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
Typing 3251 or 1,453 into the transactions search returns no rows, although the search offers to "find transactions". Counterparty names and notes match.
Expected: a number matches the amount (with or without thousands separators). Unclear whether this is wanted: see `docs/proposals/search_matching.md` before building.
