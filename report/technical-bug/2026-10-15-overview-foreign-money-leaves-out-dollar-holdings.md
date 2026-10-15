---
title: Foreign money says it is everything outside EGP but leaves out a dollar ETF
category: technical-bug
area: overview
status: reported
created: 2026-10-15
reporter: Claude
skills: website-sync
app_version: 1.1.0b1
commit: f5f551c
repo: app
---

## Report
Overview › Currencies, Mohab's sample on 2026-10-04: "Foreign money 12,126 EGP — Everything you hold outside EGP, at today’s rates." The dollar brokerage also holds 8 QQQM (Invesco NASDAQ 100 ETF), priced in USD, worth 102,085 EGP; the sidebar counts the account at 114,211.
Either the card counts foreign-currency holdings too, or its note says it is foreign cash only (`accounts/currencies.html` metric-note; Glossary has no "Foreign money" row). Severity: medium (a figure and its label disagree).
