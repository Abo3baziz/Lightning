---
name: feedback-review
description: Compile new user feedback into a batch file, investigate every item against the current code, build or decline each one with a test, record what is still open, then delete the reviewed files. Use when new feedback, survey rows or screenshots arrive, or when old feedback files should be retired.
---

# Feedback review: compile, investigate, delete

Feedback files are working papers, not documentation. They live in `user feedback/` only until their batch is finished; then
they are deleted and only three things survive: a test, a changelog line and, if something stays open, one row in
`docs/proposals/open_feedback.md`. Git history keeps the rest. The repo is public: nothing personal goes into it.

Work on one branch for the whole batch (`claude/feedback-batch-NNN`, never a vague name), push after each step, and merge to `main` at the end (AGENTS.md §6).

## 1. Compile

1. Take the new rows (Drive sheet, form export, pasted text). Number the batch after the last one in the changelog.
2. **Strip what must not be public** before writing anything: names, emails, phone numbers, account numbers, device ids, links to private folders. Write "a user". Screenshots: keep only ones showing dummy or sample data; otherwise describe the problem in words and drop the image.
3. Write `user feedback/user-feedback-batch-NNN.md`: source and date, one short ticket per row (what the person saw, what they want, screen), grouped by screen. Drop test and diagnostic rows, and say how many.
4. Mark duplicates of earlier tickets and of anything in `docs/proposals/open_feedback.md`.

## 2. Investigate

For every ticket, in this order, and write the verdict next to it:

1. **Reproduce.** Run `python -m lightning --demo --no-browser` (port 8766) and open the screen, or read the code. A ticket you cannot reproduce is not fixed: say what you tried.
2. **Is it a number?** If the report says a figure is wrong, reconcile it across tabs first; a wrong figure outranks every layout wish.
3. **Verdict**, one of: **Fixed** (a defect, now fixed), **Built** (an enhancement, now built), **Existing** (already works; say where), **Open** (a real request not built; say why), **Declined** (conflicts with the guideline or a decision; say which).
4. Questions only the owner can answer go to the owner as one GitHub issue, not into the file.

## 3. Build

- Fix Fixed/Built tickets with one test each (`tests/test_feedback_batch_NNN.py`) and the usual checks: changed-area tests, then the full suite, Mohab, guideline A16.
- Do not reopen a ticket an earlier batch marked Fixed or Existing without reproducing it.
- Changelog: one entry per batch, three lines at most.

## 4. Record what stays open, then delete

Only when every ticket has a verdict:

1. Add a row to `docs/proposals/open_feedback.md` for each **Open** ticket (request, why it is open). Delete rows there that this batch built or declined.
2. Check that each Fixed/Built ticket has a test and a changelog line. If one has not, it is not finished: go back to step 3.
3. `git rm` the batch file and its screenshots. Do not keep "for reference": git history is the reference.
4. Search for leftover references (`grep -rn "user-feedback-batch-NNN"`) and point them at the test or the changelog.
5. Commit, push the branch, merge to `main`, push.

## Rules

- Never delete a batch with an unverified ticket, or an Open ticket that is not in `open_feedback.md`.
- Never put a respondent's identity, a private link or real financial data in the repo.
- Report to the owner only: how many tickets, what was built, what is open and needs a decision.
