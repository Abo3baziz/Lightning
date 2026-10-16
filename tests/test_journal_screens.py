"""J6f: the app's own screens on a two-device journal profile."""
import asyncio

import httpx
import pytest

from test_journal_finance import devices
from lightning.sync.journal.proxy import JournalServices
from lightning.ui.web import create_app


class Screen:
    """The real app on one device, driven in the test's thread (the database is thread-bound)."""
    def __init__(self, device):
        self.app = create_app(JournalServices(device))

    def _call(self, method, path, **options):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver",
                                         headers={"origin": "http://testserver"}) as client:
                return await client.request(method, path, **options)
        return asyncio.run(run())

    def get(self, path, **options):
        return self._call("GET", path, **options)

    def post(self, path, **options):
        return self._call("POST", path, **options)


@pytest.fixture
def screens(devices):
    return devices, [Screen(device) for device in devices]


def test_pages_read_the_confirmed_copy_on_both_devices(screens):
    (hd, pc), (home, replica) = screens
    for client in (home, replica):
        for path in ("/", "/accounts", "/transactions", "/budget", "/plan", "/settings"):
            response = client.get(path)
            assert response.status_code in (200, 303), (path, response.status_code)


def test_a_replica_save_comes_back_saved_and_waiting(screens):
    (hd, pc), (home, replica) = screens
    wallet = next(a.id for a in pc.c.accounts.list() if a.name == "Wallet")
    form = dict(name="Pocket money", account_type="CASH", institution="", notes="", opening_balance_date="2026-01-01",
                owner_id="")
    response = replica.post(f"/accounts/{wallet}/edit", data=form, headers={"referer": f"http://testserver/accounts/{wallet}"})
    assert response.status_code == 303 and "msg=Saved+on+this+device" in response.headers["location"]
    assert next(a for a in pc.c.accounts.list() if a.id == wallet).name == "Wallet"  # Confirmed copy unchanged.
    pc.sync_with(hd.home)
    assert next(a for a in pc.c.accounts.list() if a.id == wallet).name == "Pocket money"
    assert hd.store.fingerprint() == pc.store.fingerprint()


def test_a_refusal_shows_at_once_on_a_replica_and_nothing_is_queued(screens):
    (hd, pc), (home, replica) = screens
    wallet = next(a.id for a in pc.c.accounts.list() if a.name == "Wallet")
    response = replica.post(f"/accounts/{wallet}/deactivate")
    assert "still+holds" in response.headers["location"] or "still%20holds" in response.headers["location"]
    assert not pc.store.pending()


def test_the_home_saves_through_the_journal_and_the_replica_follows(screens):
    (hd, pc), (home, replica) = screens
    bank = next(a.id for a in hd.c.accounts.list() if a.name == "Bank")
    form = dict(name="Main bank", account_type="BANK", institution="", notes="", opening_balance_date="2026-01-01",
                owner_id="")
    response = home.post(f"/accounts/{bank}/edit", data=form)
    assert response.status_code == 303 and "Account+saved" in response.headers["location"] or "Account%20saved" in response.headers["location"]
    assert hd.store.cursor()["revision"] == 1
    pc.sync_with(hd.home)
    assert any(a.name == "Main bank" for a in pc.c.accounts.list())
