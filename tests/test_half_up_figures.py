"""Whole-number figures round half up everywhere, so one amount reads the same on every chart and table."""
from decimal import Decimal

from lightning.ui.web import _compact, templates


def test_half_amounts_round_up_in_compact_cells_and_the_whole_filter():
    assert _compact(Decimal("468.5")) == "469"
    assert _compact(Decimal("12500")) == "13k"  # 12.5k, not banker's 12k
    assert templates.env.filters["whole"](Decimal("468.5")) == "469"
    assert templates.env.filters["whole"](Decimal("1234.5")) == "1,235"
