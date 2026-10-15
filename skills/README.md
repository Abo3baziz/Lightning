# Skills

Step-by-step procedures for any AI tool working here (Claude, Codex, others). One folder per skill, each with a `SKILL.md`.
Tool-specific folders only point here: `.claude/skills/<name>/SKILL.md` is a one-line stub so Claude Code finds the skill.
A new skill is written once, here, in plain words with no tool-only commands.

| Skill | Use it when |
|---|---|
| [feedback-review](feedback-review/SKILL.md) | New user feedback arrives, or reviewed feedback files should be retired |
| [bug-hunt](bug-hunt/SKILL.md) | Test the whole app on demo data: pages, forms, figures across tabs (`tools/bug_crawl.py`) |
| [stale-check](stale-check/SKILL.md) | Find and clean stale notes, links, proposals and branches (`tools/stale_check.py`) |
