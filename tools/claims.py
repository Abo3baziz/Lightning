"""Warn when changed files sit inside work another AI has claimed in NOW.md.

    python tools/claims.py --me Claude            # files changed on this branch vs origin/main
    python tools/claims.py --me Codex a.py b/c.py # or name the files

Exit code 1 if any file is claimed by someone other than --me.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_claims(text: str) -> list[tuple[str, list[str]]]:
    """Return (who, paths) per row of NOW.md's Claimed table; paths are the backticked Files entries."""
    claims = []
    section = text.split("## Claimed", 1)[-1].split("\n## ", 1)[0]
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Who", "") or set(cells[0]) <= {"-"}:
            continue
        claims.append((cells[0], re.findall(r"`([^`]+)`", cells[2])))
    return claims


def _matches(path: str, claimed: str) -> bool:
    claimed = claimed.rstrip("/")
    if "/" not in claimed and "." in claimed and not path.startswith(claimed + "/"):
        # a bare file name may live anywhere in the tree
        return path == claimed or path.endswith("/" + claimed)
    return path == claimed or path.startswith(claimed + "/") or path.endswith("/" + claimed)


def overlaps(claims, changed: list[str], me: str) -> list[tuple[str, str, str]]:
    found = []
    for who, paths in claims:
        if me.lower() in who.lower():
            continue
        for path in changed:
            for claimed in paths:
                if _matches(path, claimed):
                    found.append((path, who, claimed))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--me", required=True, help="your name as in NOW.md's Who column (Claude, Codex, Luna)")
    ap.add_argument("files", nargs="*", help="changed files (default: git diff --name-only origin/main...HEAD)")
    args = ap.parse_args(argv)
    files = args.files or subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    hits = overlaps(parse_claims((ROOT / "NOW.md").read_text(encoding="utf-8")), files, args.me)
    for path, who, claimed in hits:
        print(f"{path}: claimed by {who} ({claimed})")
    if not hits:
        print("No changed file is claimed by another AI.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
