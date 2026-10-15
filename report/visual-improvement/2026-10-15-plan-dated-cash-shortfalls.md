---
title: Cash planning needs a dated shortfall warning
category: visual-improvement
area: plan
status: reported
created: 2026-10-15
reporter: Codex GPT-6
skills: none
app_version: 1.1.0b1
commit: f5f551c
repo: app
---

## Report
Cash planning currently projects month-end balances; Safe to spend covers the interval until the next income. A later shortfall inside the same month can remain invisible to both.

Reproduced on a temporary sample profile at `f5f551c`: opening owned cash 1,000 on 2026-10-01, scheduled income 10,000 on 2026-10-05, rent 15,000 on 2026-10-10, second income 10,000 on 2026-10-25; no reserve allocations or savings target. `CashForecaster.forecast(2026-10-01)` returns Safe to spend 1,000, October closing 6,000 and no first short month. The scheduled dated cash path is 11,000 on the 5th, -4,000 on the 10th, then 6,000 on the 25th.

The existing monthly result is mathematically correct. The missing capability is a dated first-shortfall warning and an account-specific running balance, so positive total/month-end cash does not conceal a bill that its funding account cannot pay. Keep flexible-spending assumptions explicit; no forecast event should post money.

Evidence: `lightning/planning/forecast.py:139` aggregates by month; `lightning/planning/domain.py:189` finds short months by closing balance; `lightning/workflows/review.py` bases the cash-short warning on the monthly low. Actual's current Balance Forecast report supports daily/account views, but is experimental. Compare Competition › Actual Budget code analysis.
