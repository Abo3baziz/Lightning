---
title: The Overview still asks 444 queries; the rest are loops that need restructuring
category: technical-improvement
area: overview
status: open
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: perf-check
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
After the first round of fixes (exchange rates, prices, categories, assets read once per request) `python tools/perf_check.py` shows the Overview at 444 queries and about 110 ms.
What is left: category totals fetched month by month (44 queries on Overview and Spending), the counterparty match per register row (34 on `/accounts/<id>` and `/transactions`), per-owner holdings on `/plan`, and the physical gold item lookups.
Each is one query per row or month: batch them into one grouped query. Pages are already under 150 ms, so this is headroom for bigger profiles, not an urgent fault.
