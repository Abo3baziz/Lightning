"""Institutions: Egypt's banks as a pick list, your own additions, and tiles (feedback batch 004, T7)."""

from fastapi.testclient import TestClient

from lightning.accounts import institutions
from lightning.ui.web import create_app


def test_match_finds_the_built_in_by_name_short_name_or_arabic(c):
    for text in ("cib", "CIB", "Commercial International Bank", " commercial  international bank "):
        assert c.institutions.match(text).short_name == "CIB"
    assert c.institutions.match("البنك الأهلي المصري").short_name == "NBE"
    assert c.institutions.match("nothing like this") is None


def test_an_added_institution_is_listed_next_time_and_not_twice(c):
    assert "My Credit Union" not in [i.name for i in c.institutions.list()]
    c.institutions.add("My Credit Union")
    c.institutions.add("my credit union")
    c.institutions.add("CIB")  # a built-in: nothing new is stored
    names = [i.name for i in c.institutions.list()]
    assert names.count("My Credit Union") == 1 and sum(1 for n in names if "Commercial" in n) == 1
    assert c.institutions.match("MY CREDIT UNION").custom


def test_the_list_has_egypts_banks_brokers_and_wallets():
    kinds = {i.kind for i in institutions.builtin()}
    assert {"bank", "broker", "wallet", "fintech"} <= kinds
    names = {i.short_name for i in institutions.builtin()}
    assert {"NBE", "CIB", "THNDR", "Vodafone Cash", "Fawry"} <= names and len(institutions.builtin()) >= 40


def test_a_missing_logo_shows_the_monogram_tile():
    assert institutions.tile("My Credit Union") == {"logo": "", "mono": "MC", "name": "My Credit Union"}
    assert institutions.tile("CIB")["mono"] == "CI"
    assert institutions.monogram("Banque Misr") == "BM"


def test_used_before_comes_first_and_the_form_renders_the_options(c):
    c.account_flows.open_account("Main", "BANK", "2026-09-01", "10", institution="NBE")
    options = c.institutions.options()
    assert options[0]["group"] == "Used before" and options[0]["value"] == "NBE"
    client = TestClient(create_app(c), base_url="http://127.0.0.1")
    page = client.get("/accounts/new").text
    assert 'list="institution-options"' in page and 'data-allow-add' in page
    assert 'data-group="Used before"' in page and 'value="Commercial International Bank"' in page


def test_saving_an_account_with_a_new_institution_remembers_it(c):
    client = TestClient(create_app(c), base_url="http://127.0.0.1")
    r = client.post("/accounts/new", data={"name": "Share", "account_type": "BANK", "currency": "EGP",
                                           "institution": "My Credit Union", "opening_balance": "0",
                                           "opening_balance_date": "2026-09-01"}, follow_redirects=False)
    assert r.status_code == 303
    assert "My Credit Union" in [i.name for i in c.institutions.list()]
    listing = client.get("/accounts").text
    assert 'class="inst-tile"' in listing and ">MC<" in listing  # a custom institution shows its monogram
