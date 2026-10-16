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


def test_lab_opens_the_apps_own_screens_and_a_pc_save_reaches_the_home(tmp_path, monkeypatch):
    import socket
    from lightning.runtime import journal_lab
    devices, secret = journal_lab.open_lab(tmp_path, "dummy-launcher-password")
    home, pc = devices
    links = []
    monkeypatch.setattr(journal_lab.webbrowser, "open", lambda url: links.append(url))
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    async def run():
        task = asyncio.create_task(journal_lab.serve(devices, secret, port, full_app=True))
        try:
            for _ in range(100):
                if len(links) == 2:
                    break
                await asyncio.sleep(0.05)
            origin = f"http://127.0.0.1:{port + 1}"
            async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as stranger:
                assert (await stranger.get(origin + "/accounts")).status_code == 401
            async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
                assert (await client.get(links[1])).status_code == 200
                wallet = next(a.id for a in pc.c.accounts.list() if a.name == "Wallet")
                response = await client.post(f"{origin}/accounts/{wallet}/edit", follow_redirects=False,
                    headers={"origin": origin, "referer": f"{origin}/accounts/{wallet}"},
                    data=dict(name="Pocket money", account_type="CASH", institution="", notes="",
                              opening_balance_date=pc.c.accounts.get(wallet).opening_date, owner_id=""))
                assert "Saved+on+this+device" in response.headers["location"]
                for _ in range(100):
                    if not pc.store.pending():
                        break
                    await asyncio.sleep(0.05)
                assert not pc.store.pending()
                assert any(a.name == "Pocket money" for a in home.c.accounts.list())
                assert pc.store.fingerprint() == home.store.fingerprint()
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    try:
        asyncio.run(run())
    finally:
        for device in devices:
            device.store.close()
