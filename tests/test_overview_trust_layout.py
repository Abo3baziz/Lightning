from fastapi.testclient import TestClient

from lightning.ui.web import create_app


def test_needs_you_preview_names_first_decision_and_remaining_count(c, setup, monkeypatch):
    monkeypatch.setenv("LIGHTNING_TODAY", "2026-09-30")
    c.planning.create(kind="BILL", name="Electricity", amount="480", frequency="MONTHLY", start_date="2026-09-25")
    c.planning.create(kind="LOAN", name="Car loan", amount="2500", frequency="MONTHLY", start_date="2026-09-05",
                      payment_count="3")

    page = TestClient(create_app(c)).get("/").text
    summary = page[page.index('<summary><span class="needs-you-dot"'):page.index("</summary>", page.index('<summary><span class="needs-you-dot"'))]

    assert "Loan payment due: Car loan" in summary
    assert "Due 2026-09-05 · 2,500 EGP · not paid yet." in summary
    assert "+1 more" in summary


def test_portfolio_summary_is_one_visible_kpi_row(c, setup):
    page = TestClient(create_app(c)).get("/").text
    start = page.index('aria-label="Investments in this period"')
    row = page[start:page.index("</article>", start)]

    assert "Portfolio value" in row
    assert "Net gain or loss" in row
    assert "Income collected" in row
    assert "Open investments" in row
    assert "overview-figure-row" in row
    assert "investment-toggle" not in row
