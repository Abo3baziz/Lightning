"""UX audit: people vs businesses (counterparty kind), the institution-first account form, the Matching
disclosure on the plan form, and the broker columns of the institution list."""

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from lightning.accounts import institutions
from lightning.core.errors import ValidationError
from lightning.ui.web import create_app

import pytest

MIGRATION = Path(__file__).parent.parent / "lightning" / "database" / "migrations" / "0064_counterparty_kind.sql"


def _client(c):
    return TestClient(create_app(c), base_url="http://127.0.0.1")


# -- counterparty kind ---------------------------------------------------------------------------------------
def test_backfill_marks_every_counterparty_already_used_as_an_owner_as_a_person(c):
    account = c.account_flows.open_account("Main", "BANK", "2026-09-01", "10,000")
    mom = c.counterparties.create("Mom")
    shop = c.counterparties.create("Amazon")
    c.transactions.change_cash_ownership("2026-09-02", account.id, "500", None, mom)
    c.db.execute("UPDATE counterparties SET kind=NULL")
    sql = MIGRATION.read_text(encoding="utf-8").split("ALTER TABLE counterparties ADD COLUMN kind TEXT CHECK (kind IN ('PERSON','BUSINESS'));")[1]
    c.db.execute(sql)
    assert c.counterparties.get(mom)["kind"] == "PERSON"
    assert c.counterparties.get(shop)["kind"] is None


def test_owner_pickers_list_people_only(c):
    mom = c.counterparties.create("Mom", kind="PERSON")
    c.counterparties.create("Amazon", kind="BUSINESS")
    c.counterparties.create("Barber")
    assert [p["name"] for p in c.counterparties.list_people()] == ["Mom"]
    assert mom in [p["id"] for p in c.counterparties.list_owners()]
    page = _client(c).get("/accounts/new").text
    owner_select = re.search(r'<select id="owner_id".*?</select>', page, re.S).group(0)
    assert "Mom" in owner_select and "Amazon" not in owner_select and "Barber" not in owner_select


def test_typing_a_new_name_as_an_owner_creates_a_person(c):
    new_id = c.counterparties.ensure_person("Aunt Salma")
    assert c.counterparties.get(new_id)["kind"] == "PERSON"
    # a saved name with no kind yet counts as a person once it is used as an owner; a business stays one
    plain = c.counterparties.create("Hany")
    assert c.counterparties.ensure_person("hany") == plain
    assert c.counterparties.get(plain)["kind"] == "PERSON"
    shop = c.counterparties.create("Barber", kind="BUSINESS")
    c.counterparties.ensure_person("Barber")
    assert c.counterparties.get(shop)["kind"] == "BUSINESS"


def test_settings_toggle_marks_a_name_as_person_or_business(c):
    party = c.counterparties.create("Bawab")
    client = _client(c)
    page = client.get("/counterparties").text
    assert 'value="kind:PERSON"' in page and 'value="kind:BUSINESS"' in page
    r = client.post("/counterparties", data={"counterparty_id": str(party), "counterparty_action": "kind:PERSON"})
    assert r.status_code == 200 and c.counterparties.get(party)["kind"] == "PERSON"
    client.post("/counterparties", data={"counterparty_id": str(party), "counterparty_action": "kind:BUSINESS"})
    assert c.counterparties.get(party)["kind"] == "BUSINESS"
    with pytest.raises(ValidationError):
        c.counterparties.set_kind(party, "ROBOT")


def test_creating_from_the_counterparties_page_can_say_person(c):
    _client(c).post("/counterparties", data={"name": "Dad", "counterparty_action": "create", "kind": "PERSON"})
    assert c.counterparties.resolve("Dad")["kind"] == "PERSON"


# -- account form --------------------------------------------------------------------------------------------
def test_account_form_puts_institution_first_and_hides_held_for_and_notes_behind_more(c):
    page = _client(c).get("/accounts/new").text
    assert page.index('id="institution"') < page.index('id="account_type"') < page.index('id="name"')
    more = re.search(r'<details class="form-more" id="account-more"([^>]*)>(.*?)</details>', page, re.S)
    assert more and "open" not in more.group(1)
    assert 'id="owner_id"' in more.group(2) and 'id="notes"' in more.group(2)
    hints = json.loads(re.search(r"data-institution-hints='([^']*)'", page).group(1).replace("&#34;", '"'))
    assert hints["THNDR"]["type"] == "BROKERAGE" and hints["Vodafone Cash"]["type"] == "CASH"
    assert hints["Commercial International Bank"]["type"] == "BANK"
    assert hints["Commercial International Bank"]["short"] == "CIB"


def test_more_opens_when_it_has_a_value_or_an_error(c):
    client = _client(c)
    r = client.post("/accounts/new", data={"name": "", "account_type": "BANK", "currency": "EGP", "notes": "joint",
                                           "opening_balance": "0", "opening_balance_date": "2026-09-01"})
    assert r.status_code == 400
    assert re.search(r'id="account-more" open', r.text)


# -- plan form -----------------------------------------------------------------------------------------------
def test_matching_settings_sit_behind_a_closed_disclosure_unless_changed(c):
    from lightning.ui.routes.planning import _matching_open
    assert not _matching_open({"match_window_days": "7", "match_tolerance_pct": "10", "weekend_move": "none"}, "BILL", None)
    assert not _matching_open({"match_window_days": "7", "match_tolerance_pct": "1", "weekend_move": "none"}, "LOAN", None)
    assert _matching_open({"match_window_days": "3", "match_tolerance_pct": "10", "weekend_move": "none"}, "BILL", None)
    assert _matching_open({"match_window_days": "7", "match_tolerance_pct": "10", "weekend_move": "before"}, "BILL", None)
    assert _matching_open({}, "BILL", "match_tolerance_pct")


# -- institution list ----------------------------------------------------------------------------------------
def test_brokers_carry_their_markets_and_home_currency():
    by_code = {i.code: i for i in institutions.builtin()}
    assert by_code["interactive-brokers"].markets == ("us", "europe", "gcc") and by_code["interactive-brokers"].home_currency == "USD"
    assert by_code["efg-hermes"].markets == ("egx", "eg-funds", "gcc")
    assert by_code["beltone"].markets == ("egx", "eg-funds") and by_code["beltone"].home_currency == "EGP"
    assert by_code["cib"].markets == () and by_code["cib"].home_currency == ""
    for code in ("mubasher-trade", "beltone", "naeem", "hc-securities", "pharos", "arqaam-capital", "prime-securities",
                 "interactive-brokers", "etoro", "saxo", "swissquote"):
        assert by_code[code].kind == "broker" and by_code[code].arabic_name and by_code[code].website
    for code, markets, currency in (("al-rajhi-capital", ("gcc",), "SAR"), ("derayah", ("gcc", "us"), "SAR"),
                                    ("emirates-nbd-securities", ("gcc",), "AED"), ("trading-212", ("us", "europe"), "USD"),
                                    ("charles-schwab-intl", ("us",), "USD")):
        assert by_code[code].kind == "broker" and by_code[code].arabic_name
        assert by_code[code].markets == markets and by_code[code].home_currency == currency
    from lightning.market.packs import PACKS
    assert {m for i in by_code.values() for m in i.markets} <= set(PACKS)
    assert institutions.match_builtin("ibkr").code == "interactive-brokers"
