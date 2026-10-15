---
title: A budget of 99,999,999,999 EGP (or 150% of income) is accepted
category: technical-bug
area: budget
status: reported
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: none
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
Post `/budget/rule/<category>` with `rule=99999999999` or `rule=150%`: both save ("Budget saved."). A plan far above income makes "Plan leaves to save" negative and the health ratios meaningless.
Expected: refuse an amount above a sane limit with a plain message, or at least warn. Severity: low. Where: `BudgetService.set_budget` / `set_income_percentage`.
