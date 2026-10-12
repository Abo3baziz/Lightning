"""The Arabic UI shows no English system text: every key PC page and the phone pages, drawn in Arabic with the
Mohab sample, have no visible text, title, aria-label or placeholder with an English word (3 or more Latin
letters) except names a person typed, codes and the few identifiers listed here."""
from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from lightning.bootstrap import build
from lightning.samples import load_mohab_2026
from lightning.ui.i18n import localize_html, translate
from lightning.ui.web import create_app

PC_PAGES = ("/", "/budget", "/plan", "/plan/recurring", "/plan/loans", "/plan/reserves", "/investments",
            "/investments/prices", "/accounts", "/settings", "/search", "/rules", "/categories", "/counterparties",
            "/checks", "/financial-health", "/birdview/expenses", "/transactions", "/money-from-others")
PHONE_PAGES = ("/", "/budget", "/plan", "/investments", "/accounts", "/transactions", "/birdview/expenses",
               "/financial-health", "/settings")

# Brand, keyboard keys, data sources and the one prompt meant to be pasted into an AI tool.
ALLOWED_WORDS = {"Lightning", "Ctrl", "Enter", "Esc", "TradingView", "Yahoo", "Finance", "Mubasher", "Nasdaq",
                 "NYSE", "Arca", "Xetra", "Cboe", "BZX", "Analyze", "Excel", "UCITS"}
LATIN = re.compile(r"[A-Za-z][A-Za-z']{2,}")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip, self.found = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "textarea", "pre"):
            self.skip.append(tag)
        for name, value in attrs:
            if name in ("title", "aria-label", "placeholder", "alt") and value:
                self.found.append(value)

    def handle_endtag(self, tag):
        if self.skip and self.skip[-1] == tag:
            self.skip.pop()

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.found.append(data.strip())


def _english(page: str, names: set[str]) -> list[str]:
    parser = _Text()
    parser.feed(page)
    bad = []
    names = sorted(names, key=len, reverse=True)
    for text in parser.found:
        for name in names:
            text = text.replace(name, " ")
        text = re.sub(r"[A-Z]{2,5}-\d{4}-\d\d-\d\d-\d{3}", " ", text)
        text = re.sub(r"\S+\.[A-Za-z0-9]+", " ", text)  # file names, paths and versions
        words = [w for w in LATIN.findall(text) if not w.isupper() and w not in ALLOWED_WORDS]
        if words:
            bad.append(text[:100])
    return bad


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LIGHTNING_TODAY", "2026-10-02")
        patch.setenv("LIGHTNING_PRICES_OFFLINE", "1")
        c = build(tmp_path_factory.mktemp("ar") / "t.db")
        load_mohab_2026(c)
        yield c, _typed_names(c)
        c.db.close()


def _typed_names(c) -> set[str]:
    """Every account, counterparty, plan, asset and note in the sample: what a person typed stays as typed.
    Built-in category, asset-class and currency names are left out, so they must be shown in Arabic."""
    con = getattr(c.db, "conn", None) or getattr(c.db, "connection", None) or c.db
    names = set()
    own = {"financial_assets": "is_cash = 0 AND code NOT LIKE 'GLD:%' AND code NOT LIKE 'REF:%'"}
    for table in ("financial_assets", "accounts", "transactions", "counterparties", "counterparty_aliases",
                  "money_from_others", "cash_reserves", "planned_items", "cd_certificates",
                  "physical_item_valuations", "physical_item_trade_details", "other_asset_valuations"):
        columns = [row[1] for row in con.execute(f"PRAGMA table_info({table})")]
        for column in ("name", "notes", "description", "institution", "counterparty", "alias"):
            if column in columns:
                where = own.get(table, "1")
                names.update(r[0] for r in con.execute(f"SELECT {column} FROM {table} WHERE {where}")
                             if isinstance(r[0], str))
    return {n for n in names if len(n) > 2}


def _client(c, phone: bool):
    app = create_app(c)
    if phone:
        inner = app

        async def phone_app(scope, receive, send):
            if scope["type"] == "http":
                scope.setdefault("state", {})["phone"] = True
            await inner(scope, receive, send)
        app = phone_app
    client = TestClient(app)
    assert client.post("/settings/locale", data={"locale": "ar"}, follow_redirects=False).status_code == 303
    return client


@pytest.mark.parametrize("phone", [False, True], ids=["pc", "phone"])
def test_arabic_pages_have_no_english_system_text(sample, phone):
    c, names = sample
    # System category names are stored in English and shown translated; a person's own names stay as typed.
    user_names = names
    client = _client(c, phone)
    problems = {}
    for path in (PHONE_PAGES if phone else PC_PAGES):
        page = client.get(path)
        assert page.status_code == 200, path
        assert 'dir="rtl"' in page.text
        bad = _english(page.text, user_names)
        if bad:
            problems[path] = sorted(set(bad))[:6]
    assert not problems, problems


def test_localize_html_translates_text_and_attributes_and_leaves_data():
    page = '<p title="Save">Save</p><b>Carrefour</b><script>var a="Save";</script>'
    out = localize_html(page)
    assert 'title="حفظ"' in out and ">حفظ<" in out
    assert "Carrefour" in out and 'var a="Save"' in out


def test_patterns_and_months():
    assert translate("Delete Eating Out", "ar") == "احذف المطاعم"
    assert translate("Oct 2026", "ar") == "أكتوبر 2026"
    assert translate("Personal › Food & Groceries", "ar") == "شخصي › الأكل والبقالة"
