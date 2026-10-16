---
title: Internet sync moves one request per wake-up, so 20 offline edits need about 64 wake cycles
category: technical-improvement
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

Over the mailbox, `LocalChannel.synchronize` runs a strict request/reply sequence (capabilities, one RPC **per pending proposal**, status, then `changes`). `MailboxExchange` gives up with `CloudUnavailable` as soon as a reply is not already waiting, and the home's `changes` handler returns **one commit** per reply (`commits_after(..., limit=1)` in `local.py`). Each step therefore costs one home wake plus one device wake.

Measured with the test carrier from `tests/test_journal_cloud.py`, two home pumps per wake as `JournalInternet` does:

| Offline edits on the PC | Wake cycles until converged |
|---|---|
| 1 | 7 |
| 10 | 34 |
| 20 | 64 |

The lab wakes every 30 seconds, so 20 edits take about half an hour. With a phone home, Android's 15-minute minimum for periodic work makes it many hours. Catch-up of commits made by others costs one cycle per commit too. Every wake also ends in `CloudUnavailable`, which `RetryWindow` counts as a failure, so background attempts back off toward an hour.

Related, low: `MailboxPeer.pump` raises on the first envelope `LocalChannel.open` refuses, before acknowledging anything, so one unopenable envelope from a current member would be redelivered forever and block the queue behind it. The Worker already drops mail from removed members, so this needs a sender bug to trigger; acknowledging and recording refused envelopes would remove it.

Expected: send all pending proposals (up to the 50-proposal / 48 KiB batch in proposal §6) in one request, return as many commits as fit the 64 KiB envelope per `changes` reply, and treat "reply not yet here" as waiting, not a failure. Then re-measure against the J4 gate.
