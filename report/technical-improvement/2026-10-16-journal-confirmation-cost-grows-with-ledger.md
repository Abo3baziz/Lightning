---
title: Every journal confirmation re-reads the whole ledger, so each save gets slower as history grows
category: technical-improvement
area: journal
status: reported
created: 2026-10-16
reporter: Claude
skills: perf-check
app_version: 1.1.0b1
commit: 34f0e5a
repo: app
---

## Report

For one confirmed edit the home encodes **every** transaction twice in `CashAdapter.confirm` (the `before` map and the `changed` scan) and hashes every transaction again in `fingerprint()` from `_finish`. Each replica runs `fingerprint()` again for every commit it applies (`JournalStore.apply`). `CashAdapter.matches` also parses every journal record on each add. Cost per edit is linear in ledger size; catch-up and import are quadratic.

Measured on this build (server CPU, encrypted dummy home, one save plus confirmation):

| Transactions in the ledger | Time | SQL statements |
|---|---|---|
| 100 | 36 ms | 2,300 |
| 500 | 119 ms | 11,100 |
| 1,000 | 213 ms | 22,100 |
| 1,500 | 336 ms | 33,100 |

About 22 statements per existing transaction, on every edit. A fresh replica catching up those 1,500 commits took 90 s, because each `apply` recomputes the full fingerprint. A phone home runs Python several times slower; after a few years, or a 5,000-row CSV import confirmed one payment at a time, each confirmation takes seconds and a replica's catch-up repeats the full scan per commit.

Expected: diff only the transactions the service touched (track ids written inside `writing()`), and keep the fingerprint incremental (per-transaction hashes combined, updated in the same transaction) with a full recompute only at checkpoints and verification, as proposal §4 already allows ("verify the canonical fingerprint at checkpoints and after catch-up"). Re-measure with the `perf-check` skill.
