---
title: Twelve user requests from feedback batches 001-003 that wait for an owner decision
category: visual-improvement
area: feedback
status: open
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: feedback-review
app_version: 1.1.0b1
commit: 821db7a
repo: both
---

## Report
These are the requests left open when the `user feedback/` folder was retired (it is in git history before 2026-10-15). Everything else in those batches is fixed or already existed.
Each row needs the owner to choose build or decline; when one is decided, build it (and delete its row) or delete its row with a one-line reason in the changelog. Delete this report when the table is empty.

| Batch row | Request | Why it is open |
|---|---|---|
| 32 | Split a transfer into principal and fee during import | `update_expense_split` handles ordinary expenses only |
| 35 | A daily cash path that names the first shortfall date | Safe to spend is dated, but there is no day-by-day balance path |
| 38 | Pie chart for Spending | Treemap with exact values stays unless the owner decides |
| 50 | Trend dots show the change from the previous point | Dots show date and value only |
| 54 | Every card opens the same kind of page | Cards open transactions, plans or valuations by figure; needs one interaction contract |
| 60 | Short coloured horizon tags (S/M/L) | Full names and a filter exist; compact tags are visual only |
| 62 | Daily price timing and trading volume | Source and licensing policy of 5 October limits shared scraping |
| 63 | A different measure than "Fall from its high" | A preference, not a wrong number |
| 65 | An emergency target set freely | Would change the six-month emergency contract in Architecture |
| 73 | Review queue expires after two days | Unfinished money work must not vanish by timeout; maybe let stale suggestions be dismissed |
| 75 | Phone top bar looks too white | Check on the reporting device: Android status bar or the app bar |
| 76 | Faster five-image feedback form | Website: stage images in the background and clean up if unsent |
