---
title: After lost-home recovery a resent prefix proposal crashes confirmation for every device
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

The proposal (§7, §9) says the successor's inherited receipt set prevents replay of the retained prefix, and G2 says an identical retry returns the recorded decision. The successor does not rebuild its inbox or origin progress from the commits it inherited, so it treats an already-confirmed proposal as new.

Reproduce (home H, devices A and B, owner authority enrolled as in `tests/test_journal_authority.py`):
1. A saves a 40.00 expense; H receives and confirms it. A goes offline before it hears the decision, so the edit stays pending on A.
2. B syncs with H, so B holds the confirmed commit.
3. H is lost. B recovers (`AuthorityMemory.recover`, cutoff = B's cursor), becomes home and re-approves A.
4. A resends its pending proposal to B; B processes it.

Result: `receive` stages it (no inbox row, progress 0), `_consider` rejects it as `record-exists`, and `_finish` fails on `UNIQUE constraint failed: journal_commits.proposal_id`. The exception escapes `JournalHome.process`, so **every** later `process()` hits the same row first and the successor cannot confirm anything for any device. A also never receives its original *accepted* decision.

This is the exact case recovery exists for: a device that sent work just before the home was lost.

Severity: high (recovered home stops confirming; an accepted edit can be reported as refused).

Expected: before activation the successor rebuilds `journal_inbox` status and `journal_origins.progress` from the inherited signed commits (or `receive` consults `journal_commits` first), so a prefix proposal returns its original decision. A test should cover this alongside `test_recovery_requires_live_registry_publication_and_preserves_old_branch`.
