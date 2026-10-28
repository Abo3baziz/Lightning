---
title: Changing the language becomes an undoable action, so the Undo button silently switches it back
type: bug
area: settings
status: ready
created: 2026-10-28
by: OpenCode (GLM)
github: 167
commit: 8f80816
repo: app
---

## Report
A user changes the interface language (English → Arabic) from Settings, then presses the header Undo button — the
language silently switches back. The language change is recorded as an ordinary undoable action, so Undo/Redo replay
it like a ledger edit.

Reproduce: open Settings, switch the language, press Undo in the header (or Ctrl+Z). Expected: the language stays as
chosen; Undo undoes the last money action, not a preference. Seen on PC at `commit 8f80816`.

Evidence (reproduction with the app's own undo recorder, on a fresh profile in `python`):

```
available (empty): {'undo': None, 'redo': None}
with user_action("Saved changes"): c.settings.set("locale", "ar")
after language change: {'undo': {'id': 1, 'label': 'Saved changes'}, 'redo': None}
```

The language change sits in the undo history as "Saved changes", alongside money actions. Severity: low (no money is
wrong or lost; the preference quietly reverts).

## Investigation
Every write request is one undoable action: `lightning/ui/web.py:496` wraps any POST whose root is not in
`NOT_USER_ACTIONS` in `lightning.undo.user_action(...)` (root `settings` gets the fallback label "Saved changes").
The `locale` write lands in the profile database's `settings` table
(`lightning/ui/routes/settings.py:247`, `lightning/database/settings.py:29`), and `lightning/database/connection.py:170`
captures every INSERT/UPDATE/DELETE made under a recording action through the temp triggers of
`lightning/undo.py:63-70`. So `settings` rows — locale, also the theme, privacy mode and other preference writes from
`/settings/*` — become undo groups. Ruled out: the locale cookie is only a read path
(`lightning/ui/routes/settings.py:251`); journal profiles disable this legacy service separately
(`lightning/sync/journal/finance.py:119`).

## Fix
Undo and redo should never replay preference writes. Likely the cleanest change: add the `settings` table to `_EXCLUDED`
(`lightning/undo.py:12`) so the capture triggers never record it — undo then only spans real ledgers rows. Verify which
settings, if any, another flow expects to be replayable before applying, and keep the span across profile tables
consistent. Branch `opencode/language-change-undoable`. Test: change the language through `POST /settings/locale`,
press Undo — the stored `locale` setting must not change, and Undo must still revert the real money action before it.
