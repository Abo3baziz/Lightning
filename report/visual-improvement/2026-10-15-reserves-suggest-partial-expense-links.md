---
title: Suggest partial expense use of a funded reserve
category: visual-improvement
area: reserves
status: reported
created: 2026-10-15
reporter: Codex GPT-6
skills: none
app_version: 1.1.0b1
commit: f5f551c
repo: app
---

## Report
A reserve can already be spent in parts through explicit links, but the register/import suggestion logic only finds an expense equal to the full unpaid target of a fully funded reserve.

Reproduced on a temporary profile: create a 1,000 reserve, allocate 1,000, and associate its category/account. Record a 400 owned expense on that category/account. `suggested_reserves(transaction_id)` returns no candidates. `set_expense_link` can already record the 400 use manually; `tests/test_reserve_matching.py` also covers a manually linked 6,000 payment against a 9,000 reserve.

Evidence: `lightning/reserves.py:274` filters for full funding and exact unpaid amount. Offer an explicit partial-use suggestion when the remaining allocation and identifying evidence support it, showing the remaining reserve after the link. A broad account/category coincidence must not spend or close a reserve automatically. Support several purchases, partial funding where policy permits, refunds and undo without moving money a second time.

This is a suggestion/flow gap, not a missing ledger capability. Compare Competition › Connections worth building in Lightning.
