# Skills

Step-by-step procedures for any AI tool working here (Claude, Codex, others). One folder per skill, each with a `SKILL.md`.
Tool-specific folders only point here: `.claude/skills/<name>/SKILL.md` is a one-line stub so Claude Code finds the skill.
Every skill files its findings in `report/` (see `report/README.md`) and deletes a report when it is fixed; the folder is capped at 20 reports and 30 days each.
A new skill is written once, here, in plain words with no tool-only commands.

| Skill | Use it when |
|---|---|
| [feedback-review](feedback-review/SKILL.md) | New user feedback arrives, or reviewed feedback files should be retired |
| [bug-hunt](bug-hunt/SKILL.md) | Test the whole app on demo data: pages, forms, figures across tabs (`tools/bug_crawl.py`) |
| [stale-check](stale-check/SKILL.md) | Find and clean stale notes, links, proposals and branches (`tools/stale_check.py`) |
| [release-check](release-check/SKILL.md) | Before tagging a release (`tools/release_check.py`) |
| [guideline-audit](guideline-audit/SKILL.md) | Check screens against the brand guideline (`tests/test_brand_audit.py`, `tools/phone_check.py`) |
| [number-audit](number-audit/SKILL.md) | Prove figures match the ledger and each other, before and after money code changes |
| [perf-check](perf-check/SKILL.md) | Time pages, count queries, fix waste (`tools/perf_check.py`) |
| [arabic-check](arabic-check/SKILL.md) | Find and add untranslated Arabic strings, check RTL, digits and voice |
| [website-sync](website-sync/SKILL.md) | Keep the app and website repos consistent after a release or guideline change |

Order for a release: stale-check, release-check (which calls bug-hunt, number-audit, guideline-audit, arabic-check and perf-check), then website-sync.
