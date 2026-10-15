"""The register's scroll box clips what sits inside it (the screen-reader-only links are absolutely positioned and
would otherwise widen the whole page: 498 px of sideways scroll at a 390 px window). Checked in the stylesheet;
tools/phone_check.py and tests/test_brand_audit.py draw it in a browser."""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "lightning" / "ui" / "static" / "style.css").read_text(encoding="utf-8")


def test_register_scroll_box_is_a_positioning_context():
    rule = re.search(r"\.main \.register-table-scroll \{([^}]*)\}", CSS).group(1)
    assert "overflow-x:auto" in rule.replace(" ", "") and "position:relative" in rule.replace(" ", "")
