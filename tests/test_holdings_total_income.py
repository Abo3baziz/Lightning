"""Certificate interest belongs to the holding's gain as well as its return cash flows."""
from decimal import Decimal as D
from fastapi.testclient import TestClient

from lightning.ui.web import create_app
from test_deposit_ui import _purchase


def test_certificate_income_reaches_holding_group_totals_and_both_screens(c, setup):
    accounts, cats = setup
    cert, _ = _purchase(c, accounts)
    c.transactions.record_inflow('2026-10-01', accounts['cib'].id, '50',
                                 cats['EXP.INVEST.INTEREST'].id, counterparty='CIB')
    p = c.investments.portfolio('2026-10-31')
    h = next(h for h in p.open if h.asset_id == cert.terms.asset_id)
    assert (h.total_return, h.invested, h.display_return.percent) == (D('50'), D('5000'), D('1'))
    response = TestClient(create_app(c)).get('/investments?month=2026-10')
    assert response.status_code == 200
    page = response.text
    assert 'Total gain' in page and 'Total return' in page
    assert 'Income collected (dividends and interest)' in page
    assert '+50' in page and '+1.0%' in page


def test_total_gain_after_partial_sale_uses_original_investment(c, setup):
    accounts, _ = setup
    broker = accounts['thndr'].id
    c.transactions.record_transfer('2026-09-01', accounts['cib'].id, broker, '2000')
    asset = c.assets.create_investment('Income share', 'STOCK', 'INCOME')
    c.investments.buy_total('2026-09-02', broker, asset.id, '10', '1000')
    c.investments.sell_total('2026-09-10', broker, asset.id, '5', '600')
    c.investments.dividend('2026-09-15', broker, asset.id, '50')
    c.assets.set_price(asset.id, '2026-09-30', '110')
    h = c.investments.portfolio('2026-09-30').open[0]
    result = h.owned_result(h.quantity, h.value, h.cost_basis)
    assert result == {'gain': D('200'), 'invested': D('1000'), 'gain_pct': D('20')}
    assert h.display_return.percent == D('20')

    # Balance-only holdings also belong in the total's denominator: the 5,000 legacy CD
    # and this 1,000 flat, plus the share's original 1,000 purchase, make 7,000.
    c.account_flows.open_account('Share of flat', 'OTHER_ASSET', '2026-09-01', '1000')
    page = TestClient(create_app(c)).get('/investments?month=2026-09').text
    total = page.split('<tbody class="holding-total">', 1)[1].split('</tbody>', 1)[0]
    assert '+200' in total and '+2.9%' in total
