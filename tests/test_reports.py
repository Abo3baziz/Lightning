"""report/ holds only unprocessed findings, each well-formed, and its index is current (tools/report_index.py)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_every_report_is_well_formed_unprocessed_and_indexed():
    spec = importlib.util.spec_from_file_location("report_index", ROOT / "tools" / "report_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows, problems = module.load()
    assert not problems, problems
    assert (ROOT / "report" / "INDEX.md").read_text(encoding="utf-8") == module.render(rows), "run python tools/report_index.py"
