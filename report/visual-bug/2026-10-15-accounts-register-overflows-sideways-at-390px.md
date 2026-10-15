---
title: The account register and Transactions pages scroll sideways when the window is narrow
category: visual-bug
area: accounts
status: reported
created: 2026-10-15
reporter: Claude Sonnet 5.5
skills: none
app_version: 1.1.0b1
commit: 821db7a
repo: app
---

## Report
At a 390 px wide window the desktop layout of `/accounts/<id>` and `/transactions` is about 498 px wide (108 px of sideways scroll). Other pages fit.
The phone app has its own layout (guideline Part C), so this matters only for a narrowed PC window, and for the browser version. Expected: the register table fits or scrolls inside its card (A11). Severity: low.
Found with a 1280 and 390 px browser pass.
