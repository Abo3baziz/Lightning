---
title: The CSV import preview does not warn about a future-dated row; Post refuses it later
category: technical-bug
area: import
status: reported
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: none
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
Import a statement with a row dated after today (for example 2026-12-30). The review page lists it as "Needs a decision" like any row, with no future-date warning.
Pressing Post then fails with "2026-12-30 is in the future" and lists it under rows to fix. Manual entry refuses future dates at once. Expected: the preview marks the row to fix straight away. Severity: low. Where: `lightning/bank_imports.py` preview validation.
