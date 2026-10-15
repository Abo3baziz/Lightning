# Open user feedback

**Status:** proposal, 2026-10-15 · Claude, not built. What is still open from feedback batches 001–003 after their folder was retired
(`user feedback/`, in git history before 2026-10-15). Everything else in those batches is fixed, already existed or was declined, and is in
the changelog and `tests/test_feedback_batch_003.py`, `tests/test_mohab_year.py`. When an item is built or decided, delete its row.

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
