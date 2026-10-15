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
Measured with Playwright at 360 px on the demo data (every page in `tools/phone_check.py`). Nothing scrolls sideways.
- **C10 small type under 12px:** tab-bar names (`.phone-tab-name`, 11px, every page); Birdview expenses chart labels (10 to 11px, `b` and `i` in the by-category and usual-against-now chart).
- **C12 cut word or "…":** Birdview expenses category names (`Food & Groceries`, `Eating Out`, `Other`) and `440 · 2%` truncate with ellipsis; Overview chip `76% used`.
- **C12 hover or tooltip only:** Birdview `i.now` and `i.usual` bars say Now / Usual amounts only in `title`.
- **C12 a table:** visible `<table>` on `/investments/prices`, `/counterparties`, `/money-from-others`, `/settings`, `/zakat`, `/birdview/expenses`, `/financial-health`. Part C wants rows, with the rest in a sheet.
- **C09.2 fields 48 tall:** register-row wells are 30px on `/budget` and `/counterparties`; `Find a category` and the month box 36px; `/checks` dates 40px; the language select on `/profiles` 36px.
- **C05.1 row and icon targets:** the counterparty delete icon is 28px (needs 44), and `Save alias` measures 1px tall.

Not verified, look at a screenshot first: cards that hold three or more rows (C12 "a card around a list of rows") on Overview, Plan, Budget, Investments, Accounts, Financial health; typed `yyyy-mm-dd` text inputs may have a picker button beside them.
Fixed in the same pass, so not listed here: buttons stayed at desktop height on the phone because `style.css` sets them behind `:not(#_)`.
