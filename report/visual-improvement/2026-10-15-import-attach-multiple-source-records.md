---
title: Allow multiple source records to support one existing transaction
category: visual-improvement
area: import
status: reported
created: 2026-10-15
reporter: Codex GPT-6
skills: none
app_version: 1.1.0b1
commit: f5f551c
repo: app
---

## Report
Manual entries, bank SMS and CSV statements may describe the same owned payment. SMS already enters the same import service. A later statement should be able to contribute evidence to the existing transaction without posting money or losing useful bank metadata.

Reproduced on a temporary profile: record an owned -75 payment dated 2026-10-01. Import a first source row and confirm a link to that transaction. Import a second file with the same date, account and -75 amount but no bank reference. Preview returns zero link candidates and defaults to Skip. It can avoid a duplicate, but cannot attach the second source to the same account's existing transaction through the linking flow.

Cause: `BankImportService._link_candidates` excludes a transaction already supported by a POSTED/LINKED import row on this account; `_link_import_row` also enforces that model. A repeated file should still be idempotent, and two real equal payments must remain distinct. Distinguish a repeated source row from a different source's evidence, preserve original/source dates, and allow explicit multi-source confirmation with an audit trail.

Related existing work: `docs/proposals/import_matching.md` concerns the three-day window; `merge_transactions.md` concerns two already-posted transactions. This finding concerns several source records supporting one ledger transaction. A four-day delayed payment also currently has no candidate and defaults to New; that is the deliberate existing window, not a newly diagnosed defect. Do not simply widen it or auto-link on amount/date alone.
