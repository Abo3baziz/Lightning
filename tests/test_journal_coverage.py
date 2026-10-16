"""Write coverage of the app's screens on a journal profile: an honest inventory, and graceful refusals."""
import sys
from pathlib import Path

import pytest

from test_journal_finance import devices  # noqa: F401
from test_journal_screens import screens  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import journal_coverage  # noqa: E402


def test_the_inventory_reports_the_account_edit_route_as_covered():
    rows = journal_coverage.inventory()
    state = {row["path"]: row["state"] for row in rows}
    assert state["/accounts/{account_id:int}/edit"] == "covered"
    assert state["/sms/assign"] == "uncovered" and state["/settings/locale"] == "covered"
    assert {"covered", "uncovered", "read-only"} <= set(state.values())
    assert journal_coverage.regressions(rows) == []
    assert "Summary:" in journal_coverage.report(rows)


@pytest.mark.parametrize("who", [0, 1], ids=["home", "replica"])
def test_an_uncovered_write_is_refused_gracefully_and_writes_nothing(screens, who):
    (hd, pc), clients = screens
    device, client = (hd, pc)[who], clients[who]
    before = device.store.fingerprint()
    # Naming the account of a bank-message ending is not covered (it stores local account ids and stages an import).
    bank = next(a.id for a in device.c.accounts.list() if a.name == "Bank")
    response = client.post("/sms/assign", data={"ending": "1234", "account_id": str(bank)}, headers={"referer": "http://testserver/sms"})
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/sms?msg=This+is+not+available+on+a+synchronized+profile+yet")
    assert device.store.fingerprint() == before and not device.store.pending()
    assert not device.c.settings.get("sms_account_endings")
    assert client.get(location).status_code == 200  # The screen the user lands on renders.


def test_other_database_errors_are_not_hidden(screens, monkeypatch):
    (hd, pc), (home, replica) = screens
    import sqlite3

    def broken(*args, **kwargs):
        raise sqlite3.DatabaseError("disk image is malformed")
    monkeypatch.setattr(hd.c.sms_imports, "assign", broken)
    with pytest.raises(sqlite3.DatabaseError, match="malformed"):
        home.post("/sms/assign", data={"ending": "1234", "account_id": "1"})
