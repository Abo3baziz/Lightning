---
title: First-device pairing sends an offline-crackable password proof to any nearby device claiming to be home
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

`request_pairing` (`lightning/sync/journal/pairing.py`) proves the password as `HMAC(Argon2id(password, offer_salt), code || request)`. For a brand-new replica, `NewJournalReplica.join` (`lightning/runtime/journal_enrollment.py`) takes `home_key`, the salt and the TLS certificate from the discovery reply. That reply is self-certifying only: it is signed by the key it carries.

During the pairing window, anyone on the same network can answer discovery with a look-alike device name and their own offer. If the user picks it and types the code and profile password, the attacker receives a proof bound to a salt they chose. The six-digit code adds no protection offline (10^6 cheap HMACs per password guess), so the attacker can run a dictionary attack against the **profile password** at one Argon2id evaluation per guess. Matching check digits fail afterwards, but the proof has already left the device. The compatible-replica path (`NearbyPairing.join`) is not affected because it already knows `home_key`.

The proposal says "do not invent cryptographic primitives" and requires the J5 constructions to be reviewed; this one needs that review before first-device enrollment ships.

Severity: medium (security; dummy profiles only today, but it targets the master password).

Expected (one of): a reviewed PAKE (CPace, SPAKE2 or OPAQUE) so the transcript gives no offline verifier; or confirm the matching digits (short authentication string over the TLS-pinned home key) **before** sending anything derived from the password.
