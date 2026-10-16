---
title: A review on the home plus 256 queued edits stops that device receiving any confirmed changes
category: technical-bug
area: journal
status: investigating
created: 2026-10-16
reporter: Claude
skills: none
app_version: 1.1.0b1
commit: 34f0e5a
repo: app
---

## Report

Strict per-origin order means one proposal in review holds back every later edit from that device. `JournalHome.receive` raises `Sequence gap exceeds staging window` once a device has more than 256 edits beyond its progress. `LocalChannel.synchronize` (and `sync_with`) uploads proposals **before** asking for changes, so that error aborts the round: the device stops downloading other devices' confirmed changes until the review is resolved on the home. On the home itself, `JournalDevice.save` raises the same error after the edit is already durably saved, so the user is told a saved edit failed.

The trigger is easy to hit because `CashAdapter.matches` sends **every** add with the same account, date and amount as an existing record to `possible-duplicate` review, including two ordinary manual entries (two 50.00 taxi fares on one day). A CSV import may stage up to 5,000 payments, so one look-alike row can block hundreds behind it.

Reproduce: device A adds 50.00, syncs, adds another 50.00 on the same day, then 257 more edits; the home adds one edit; A syncs. A's sync raises `JournalError: Sequence gap exceeds staging window`; A's cursor stays at revision 1 while the home is at 2.

Severity: medium (no money lost; sync silently stalls and a saved edit is reported as failed).

Expected:
- Download changes even when upload hits the staging limit (or stop uploading at the window and continue the round).
- Report a staging refusal as "saved, waiting", never as a failed save.
- Consider limiting fuzzy duplicate review to captured payments (with a `source`) or to different origins, per the proposal's SMS/CSV row; a manual same-day repeat from one device is usually intentional.

## Fix

Claude, `claude/journal-hardening`: a held upload on the home no longer reports a saved edit as failed, and fuzzy duplicate review needs a captured payment. Still open: download changes when upload is held (transport round, in progress).
