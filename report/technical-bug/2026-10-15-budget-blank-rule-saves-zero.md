---
title: Saving a blank budget field sets the budget to 0 and says Budget saved
category: technical-bug
area: budget
status: open
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: none
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
Post `/budget/rule/<category>` with an empty `rule` (the field cleared in the UI): the app answers "Budget saved." and the category's planned amount becomes 0.
The route's own docstring (`lightning/ui/routes/budget.py`, `inline_rule`) says an empty field *clears the category's own rule*. Zero and "no rule" are different: with no rule the category may fall back to its average.
Severity: low. Needs an owner decision: should a blank field remove the rule (back to the default) or be refused?
