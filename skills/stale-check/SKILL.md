---
name: stale-check
description: Find stale or inconsistent things in the repository (old hand-off messages and claims, dead links, built proposals, merged branches, version and guideline drift) and clean up the safe ones. Use before a release, when the repo feels cluttered, or on request.
---

# Stale check

Tool-neutral. The repo is public: stale files mislead readers and leak history. Read-only first, then clean up.

## Steps

1. `git fetch origin`, then `python tools/stale_check.py` (`--days N` changes the seven-day limit). It reports:
   - `NOW.md` messages and claims older than the limit;
   - Markdown links to files that no longer exist;
   - proposals that say they are built;
   - branches already merged into `main`, and branches holding commits `main` lacks;
   - README version against `pyproject.toml`;
   - guideline copies that differ from a sibling `Lightning_website` checkout.
2. **Also look for** (the script cannot): `docs/` figures or dates that contradict the code, tests marked `known_gap` whose gap is fixed, files nothing references, and copied text that appeared in two files (keep one, link the other).
3. **Fix the safe ones now**, one branch per kind of cleanup (AGENTS.md §6): delete your own old messages, repair or remove dead links, move what holds from a built proposal into Architecture and delete it, align the version, copy the newer guideline over the older in both repos.
4. **Ask the owner first** for anything outward-facing or someone else's: deleting remote branches, another AI's claims or messages, branches with unmerged commits (list them with their last commit date and subject), anything under `.github/`.
5. Changelog entry (three lines at most), tests for the areas touched, push, merge.

## Report

**Where findings go.** Read `report/README.md` once. Fix a small finding now (branch, test, changelog line) and file **no** report. File anything bigger as one report in
`report/<category>/` (this skill's name in `skills`, your model in `reporter`, `app_version` from `pyproject.toml`, `commit` from `git rev-parse --short HEAD`), then run
`python tools/report_index.py`. Fixing a report means deleting its file in the same commit. Never leave a finding only in chat, and never let the folder pile up (20 reports, 30 days).

Counts per kind, what you fixed, and a short list of decisions for the owner. Do not list every stale branch.
