"""tools/claims.py reads NOW.md's Claimed table and flags files claimed by someone else."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("claims", ROOT / "tools" / "claims.py")
claims = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(claims)

NOW = """# Now

## Claimed

| Who | Work | Files | Since |
|---|---|---|---|
| Codex | 02d | `tests/test_x.py` | 2026-10-06 |
| Claude | M3 | `lightning/sync/`, `phone.css`, `android/` | 2026-10-06 |
| Luna, for Codex | 03a | `lightning/runtime/restore.py` | 2026-10-05 |

## Messages
"""


def test_parser_reads_who_and_backticked_paths():
    parsed = claims.parse_claims(NOW)
    assert parsed[1] == ("Claude", ["lightning/sync/", "phone.css", "android/"])
    assert [who for who, _ in parsed] == ["Codex", "Claude", "Luna, for Codex"]


def test_overlap_ignores_own_claims_and_matches_directories():
    parsed = claims.parse_claims(NOW)
    changed = ["lightning/sync/pull.py", "lightning/ui/static/phone.css", "lightning/runtime/restore.py", "README.md"]
    assert [h[0] for h in claims.overlaps(parsed, changed, "Claude")] == ["lightning/runtime/restore.py"]
    assert len(claims.overlaps(parsed, changed, "Codex")) == 2


def test_the_real_now_md_parses():
    assert claims.parse_claims((ROOT / "NOW.md").read_text(encoding="utf-8"))
