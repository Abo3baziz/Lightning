---
name: perf-check
description: Measure how long each Lightning page takes and how many database queries it asks, find the repeated or wasteful ones, and fix them without changing any output. Use when pages feel slow, after adding a screen or report, before a release, or when asked to make the app more efficient.
---

# Performance check

Tool-neutral. Lightning ships as a Windows app (WebView2) over local SQLite, encrypted. Mohab's acceptance test sets the bar: pages must feel instant on an ordinary PC,
long periods stay summarised (months, not 365 days), pages stay light. A page is fine under about 150 ms warm and about 400 queries; below that, do not optimise.

## Token rules

Measure first, change the one worst thing, measure again. Never read a service file to "look for slow code": the measurement names the query and the page, then grep for that SQL text.

## Steps

1. **Measure.** `python tools/perf_check.py` builds a temporary profile (the sample household: ten months, about 300 rows; `--demo` for the small one), asks each main page twice (cold, then warm)
   and prints warm milliseconds, query count and the most repeated query. It exits 1 when a page is over `--slow` ms (default 150) or `--queries` (default 400). Nothing real is touched.
2. **Scale it.** The sample is smaller than a real year. For a bigger case, load the sample then add rows in a loop with `container.transactions.record_outflow(...)` before measuring, or look at
   `tests/test_reporting_performance.py` (a 319-transfer fixture). Long periods must still render months, not days.
3. **Pick the worst offender** by queries first (queries scale with data; milliseconds on a fast disk hide them). A query repeated N times with different parameters is a loop to batch; the same text with the same
   parameters is a missing memo.
4. **Fix with the existing tools, smallest first:**
   - **Per-request memo:** decorate a pure read with `@request_cached` from `lightning/core/memo.py`. It lasts for one request and is cleared by any database write; it is off inside a transaction and outside a request.
     Arguments must be hashable. Add `deep=True` if callers might edit the returned object. Settings are already memoised through `raw_setting` in `lightning/database/settings.py`: read settings through it, not with a raw `SELECT`.
   - **Batch the lookup:** replace "one query per row" with one `WHERE id IN (...)` or one join, as `tests/test_reporting_performance.py` shows for asset metadata.
   - **Pure function cache:** `functools.lru_cache` for pure, hashable-in/immutable-out functions (see `parse_month` in `lightning/core/dates.py`).
   - **Index** only if a single query is slow by itself (check with `EXPLAIN QUERY PLAN`), and only through a numbered migration.
   Never cache across requests, and never cache a figure that a write in the same request can change without the memo being cleared.
5. **Prove nothing changed.** The page's text must be identical before and after: fetch it before, change, fetch after, compare (strip session tokens). Add a test that counts queries (copy the pattern in
   `tests/test_reporting_performance.py::test_main_tabs_read_each_figure_once_and_show_the_same_pages_as_without_the_cache`). Run the suite and Mohab.
6. **Record:** one changelog entry with the before and after numbers (queries and milliseconds), one branch per fix, merge.

## Known hotspots (last measured 2026-10-15 on the sample year)

Overview `/`: 642 queries, 114 ms (`fx_rates` rate lookup repeated 80 times; price lookups). `/plan` and `/financial-health`: about 370 queries (`price_history` lookup 47–53 times).
`/investments`: 291 queries (`fx_rates` 52 times). `/accounts/1` and `/transactions`: `counterparties` match query 34 times. `/counterparties`: `categories` read 37 times. These are ideas, not facts: re-measure before acting.

## Report

A table of page, warm ms, queries before and after, and the single change that did it. Say what you did not touch and why (under the limits).
