"""Feedback batch 004 (tickets 96-112, 2026-10-16): one test per ticket. Retire when the batch is old."""
from pathlib import Path

from fastapi.testclient import TestClient

from lightning.ui.web import create_app

ROOT = Path(__file__).parents[1]


def test_undo_is_a_header_icon_with_a_shortcut():
    """Ticket 101: Undo is an icon in the page header (Ctrl+Z); no text button spills into the page."""
    base = (ROOT / "lightning/ui/templates/base.html").read_text(encoding="utf-8")
    top = base[base.index('<div class="topbar">'):base.index('{% include "partials/section_tabs.html" %}')]
    assert 'partials/history.html' in top and base.count('partials/history.html') == 1
    history = (ROOT / "lightning/ui/templates/partials/history.html").read_text(encoding="utf-8")
    assert 'icon-btn history-btn' in history and "Ctrl+Z" in history and "btn small" not in history
    js = (ROOT / "lightning/ui/static/app.js").read_text(encoding="utf-8")
    assert 'data-history="${operation}"' in js and 'e.shiftKey ? "redo" : "undo"' in js


def test_a_crash_shows_a_calm_page_not_the_server_text(c, setup):
    """Ticket 108: an unexpected failure and an unknown address each get an app page with a way forward."""
    app = create_app(c)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internals")

    client = TestClient(app, raise_server_exceptions=False)
    crashed = client.get("/boom")
    assert crashed.status_code == 500
    assert "Something went wrong" in crashed.text and "secret internals" not in crashed.text
    assert "Internal Server Error" not in crashed.text and 'href="/"' in crashed.text
    missing = client.get("/no-such-page")
    assert missing.status_code == 404 and "Back to the dashboard" in missing.text


def test_shares_show_their_ticker_and_funds_are_not_an_exchange(c, setup):
    """Tickets 104, 110: the holdings table names a share by its ticker; By market keeps funds apart from EGX."""
    from lightning.investments.domain import Position
    from lightning.investments.views import regroup

    share = Position(1, "Broker", 1, "STK:COMI", "Commercial International Bank", "Stocks", "Equity", "share",
                     1, 1, 0, 0, None, None, "", None)
    fund = Position(1, "Broker", 2, "FND:AZ-GOLD", "Azimut Gold Fund", "Funds › Gold", "Gold", "unit",
                    1, 1, 0, 0, None, None, "", None)
    assert share.short_name == "COMI" and fund.short_name == "Azimut Gold Fund"

    class Asset:
        def __init__(self, code):
            self.code, self.mic, self.currency = code, "XCAI", "EGP"

    from decimal import Decimal
    rows = [{"h": share, "value": Decimal(10), "cost": Decimal(1), "asset_id": 1},
            {"h": fund, "value": Decimal(5), "cost": Decimal(1), "asset_id": 2}]
    groups = regroup("market", [{"name": "Stocks", "rows": rows}], Decimal(15), accounts={}, base="EGP",
                     assets={1: Asset("STK:COMI"), 2: Asset("FND:AZ-GOLD")})
    assert {g["name"] for g in groups} == {"EGX", "Funds"}
