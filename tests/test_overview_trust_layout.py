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


def test_the_overview_has_no_investments_row(c, setup):
    """Feedback 100: the one-line Investments row is gone; the Investments tab holds those figures."""
    page = TestClient(create_app(c)).get("/").text
    assert 'aria-label="Investments in this period"' not in page and "investments-heading" not in page