---
title: One proposal that raises an unexpected error stops the home confirming for every device
category: technical-bug
area: journal
status: reported
created: 2026-10-16
reporter: Claude
skills: none
app_version: 1.1.0b1
commit: 34f0e5a
repo: app
---

## Report

`JournalHome._finish` (`lightning/sync/journal/home.py`) turns only `ValidationError` from the financial services into a `financial-validation` refusal. The services also raise `NotFoundError` and `ConflictError` (siblings of `ValidationError` under `LightningError`), and the database can raise `IntegrityError`. Any of these escapes `process()`, which rolls back and stops. The next `process()` picks the same row again, so one proposal blocks **all** origins, not just its own. The proposal requires "other origins continue while this origin waits" (§4, G6).

Evidence: with `record_in_account` made to raise `NotFoundError` for one amount, device A's sync raises and device B's unrelated, valid edit then fails with the same `NotFoundError` on every attempt. The recovery report (`2026-10-16-journal-recovery-replays-prefix-and-jams-home.md`) is a real trigger of the same weakness through `IntegrityError`.

Severity: medium (no money is wrong, but the whole profile stops confirming until someone edits the database).

Expected: catch `LightningError` as a refusal; for any other exception, park that proposal in review with a bounded reason such as `home-error` (its origin waits, others continue) and keep the evidence.
