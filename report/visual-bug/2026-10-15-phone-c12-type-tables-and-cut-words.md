---
title: Phone screens break C10 and C12 on small type, tables, cut words and 30px fields
category: visual-bug
area: phone
status: open
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: guideline-audit
app_version: 1.1.0b1
commit: 3d098f8
repo: app
---

## Report
Measured with Playwright at 360 px on the demo data (every page in `tools/phone_check.py`). Fixed since (type 12px, treemap as rows, cluster chart two a row, fields 48, icons 44, buttons 48/40); tables are now stacked rows (CSS plus a label pass in `phone-fields.js`); what is still open:
- **Birdview now-against-usual chart:** on a phone each row of clusters leaves about 120px of empty space under the percentage; tighten it.

Not verified, look at a screenshot first: cards that hold three or more rows (C12 "a card around a list of rows") on Overview, Plan, Budget, Investments, Accounts, Financial health; typed `yyyy-mm-dd` text inputs may have a picker button beside them.
