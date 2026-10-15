"""U1 page jump, U14 loading note, U15 three-band ratio thresholds."""
import re
from decimal import Decimal as D

import pytest

from lightning.core.errors import ValidationError
from lightning.planning.health import HealthFigure, LIMIT_PREFIX, band_of
from lightning.ui.routes import financial_health as route


CSS = open("lightning/ui/static/style.css", encoding="utf-8").read()
JS = open("lightning/ui/static/app.js", encoding="utf-8").read()


def test_page_jump_stays_bottom_right_and_wakes_near_the_corner():
    for rule in re.findall(r"\.page-jump\s*\{[^}]*\}", CSS):
        assert "left:" not in rule.replace("right:", "")
    assert "pointermove" in JS and "window.innerHeight - event.clientY < 140" in JS
    assert ".page-jump { opacity:0;" in CSS and ".page-jump.is-visible" in CSS


def test_loading_note_is_muted_and_bottom_right():
    square = re.search(r"\.busy-square\s*\{[^}]*\}", CSS).group(0)
    toast = re.search(r"\.busy-toast\s*\{[^}]*\}", CSS).group(0)
    assert "background:var(--muted)" in square and "azure" not in square
    assert "bottom:" in toast and "top:" not in toast and "right:" in toast
    assert 'show("Opening…"), 300' in JS


@pytest.mark.parametrize(("value", "band"), [(D("75"), "alert"), (D("50"), "watch"), (D("30"), "good"), (D("70"), "watch")])
def test_debt_to_net_worth_bands(c, value, band):
    assert c.health.band("debt_to_net_worth", value) == band


def test_savings_rate_is_a_minimum_band(c):
    assert [c.health.band("savings_rate", D(v)) for v in ("25", "15", "5")] == ["good", "watch", "alert"]
    assert c.health.band("savings_rate", None) is None and band_of(D(1), None, None, "maximum") is None


def test_edited_thresholds_change_the_band(c):
    assert c.health.band("debt_to_net_worth", D("50")) == "watch"
    c.health.set_limit("debt_to_net_worth", "55", alert_raw="80")
    assert c.health.band("debt_to_net_worth", D("50")) == "good"
    assert c.health.band("debt_to_net_worth", D("75")) == "watch" and c.health.band("debt_to_net_worth", D("85")) == "alert"


def test_thresholds_must_lie_on_the_right_sides(c):
    with pytest.raises(ValidationError):
        c.health.set_limit("savings_rate", "20", alert_raw="25")
    with pytest.raises(ValidationError):
        c.health.set_limit("fixed_costs_to_income", "50", alert_raw="40")


def test_the_old_single_limit_becomes_the_good_boundary(c):
    c.settings.set(LIMIT_PREFIX + "fixed_costs_to_income", "40")
    assert c.health.limit_values()["fixed_costs_to_income"] == D("40")
    assert c.health.band("fixed_costs_to_income", D("40")) == "good" and c.health.band("fixed_costs_to_income", D("45")) == "watch"
    c.health.restore_limit("fixed_costs_to_income")
    assert c.health.limit_values()["fixed_costs_to_income"] == D("50")


def test_needs_you_card_is_rose_and_says_so():
    def fig(band):
        return HealthFigure("debt_to_net_worth", D("75"), "%", "2026-10-15", D("30"), "maximum", "outside your limit",
                            (), "/plan/loans", alert=D("70"), band=band)
    alert, watch = route._kpi(fig("alert"), "Debt to net worth"), route._kpi(fig("watch"), "Debt to net worth")
    assert alert["surface"] == "over" and alert["badge"]["text"] == "Needs you" and alert["band"] == "alert"
    assert watch["badge"]["text"] == "Watch" and watch["badge"]["tone"] == "" and watch["surface"] != "over"
    macro = open("lightning/ui/templates/partials/charts.html", encoding="utf-8").read()
    assert "is-alert" in macro and ".main .stat-tile.is-alert { background:var(--rose-soft); }" in CSS
