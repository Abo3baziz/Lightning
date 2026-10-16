"""A paired LAN home wins; cloud failure keeps the same durable edit pending."""
import asyncio
import os

import pytest

from test_journal_finance import devices, groups
from lightning.runtime.journal_routes import LocalFirstSync
from lightning.sync.journal.codec import JournalError
from lightning.sync.journal.discovery import LanResponder, _open, _scope, discover
from lightning.sync.journal.local import LocalChannel


def channels(devices):
    home, pc = devices
    secret = os.urandom(32)
    return (LocalChannel(home, transport_key=secret, peers={pc.identity.device_id:pc.identity.public_key}),
            LocalChannel(pc, transport_key=secret, peers={home.identity.device_id:home.identity.public_key}))


def test_paired_local_link_is_default_and_does_not_contact_cloud(devices):
    home, pc = devices
    server, client = channels(devices)
    class Cloud:
        async def catch_up(self, **kwargs):
            pytest.fail("Reachable LAN must win over cloud")
    async def discovery(*args):
        pytest.fail("The verified saved local endpoint is already reachable")
    def factory(endpoint, certificate, timeout):
        async def request(wire):
            return server.handle(wire)
        return request
    pc.save(groups(pc))
    route = LocalFirstSync(pc, client, home_id=home.identity.device_id, certificate="saved paired certificate",
                          endpoints=["https://192.168.1.2:47513/exchange"], internet=Cloud(),
                          discovery=discovery, client_factory=factory)
    assert asyncio.run(route.synchronize())
    assert not pc.store.pending()
    assert home.store.fingerprint() == pc.store.fingerprint()
    assert pc.c.db.scalar("SELECT value FROM journal_local WHERE name='sync_route'") == "local"


def test_missing_local_network_uses_cloud_and_quota_failure_keeps_saved_edit(devices):
    home, pc = devices
    _, client = channels(devices)
    attempted = []
    class Cloud:
        async def catch_up(self, **kwargs):
            attempted.append("cloud")
            return False  # E.g. provider free quota is exhausted.
    def factory(endpoint, certificate, timeout):
        async def request(wire):
            attempted.append("local")
            raise OSError("Different network")
        return request
    async def discovery(*args):
        attempted.append("discover")
        return []
    original = pc.save(groups(pc))
    route = LocalFirstSync(pc, client, home_id=home.identity.device_id, certificate="saved paired certificate",
                          endpoints=["https://192.168.1.2:47513/exchange"], internet=Cloud(),
                          discovery=discovery, client_factory=factory)
    assert not asyncio.run(route.synchronize())
    assert attempted == ["local", "discover", "cloud"]
    assert pc.store.pending() == [original]
    assert home.store.cursor()["revision"] == 0


def test_discovered_new_address_is_verified_and_saved_without_pairing_again(devices):
    home, pc = devices
    server, client = channels(devices)
    attempted = []
    def factory(endpoint, certificate, timeout):
        async def request(wire):
            if "192.168.1.2:" in endpoint:
                attempted.append("old-address")
                raise OSError("DHCP changed address")
            return server.handle(wire)
        return request
    async def discovery(*args):
        return ["https://192.168.1.3:47513/exchange"]
    pc.save(groups(pc))
    route = LocalFirstSync(pc, client, home_id=home.identity.device_id, certificate="saved paired certificate",
                          endpoints=["https://192.168.1.2:47513/exchange"], discovery=discovery, client_factory=factory)
    assert asyncio.run(route.synchronize())
    assert len(attempted) == 1
    assert route.endpoints[0] == "https://192.168.1.3:47513/exchange"
    assert home.store.fingerprint() == pc.store.fingerprint()


def test_discovery_accepts_only_the_paired_signature_and_fresh_nonce(devices):
    from lightning.sync.journal.codec import seal
    home, pc = devices
    server, client = channels(devices)
    nonce = os.urandom(32).hex()
    body = dict(type="journal-found",scope=_scope(server),sender=home.identity.device_id,
                recipient=pc.identity.device_id,nonce=nonce,port=47513)
    wire = seal(body, home.identity.sign)
    assert _open(client, wire, kind="journal-found",recipient=pc.identity.device_id,nonce=nonce) == body
    with pytest.raises(JournalError):
        _open(client, wire, kind="journal-found",recipient=pc.identity.device_id,nonce=os.urandom(32).hex())
    with pytest.raises(JournalError):
        _open(client, seal(body, pc.identity.sign), kind="journal-found",recipient=pc.identity.device_id,nonce=nonce)


def test_real_udp_discovery_finds_paired_home_on_local_network(devices):
    home, pc = devices
    server, client = channels(devices)
    async def run():
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(lambda: LanResponder(server, tls_port=47513), local_addr=("127.0.0.1",0))
        try:
            port = transport.get_extra_info("sockname")[1]
            found = await discover(client, home.identity.device_id,port=port,timeout=1,destinations=("127.0.0.1",))
            assert found == ["https://127.0.0.1:47513/exchange"]
        finally:
            transport.close()
    asyncio.run(run())


def test_protocol_refusal_is_reported_without_hiding_it_behind_another_route(devices):
    home, pc = devices
    _, client = channels(devices)
    def factory(*args, **kwargs):
        async def request(wire):
            raise JournalError("Update this device")
        return request
    route = LocalFirstSync(pc, client,home_id=home.identity.device_id,certificate="paired",
        endpoints=["https://192.168.1.2:47513/exchange"], client_factory=factory)
    with pytest.raises(JournalError,match="Update this device"):
        asyncio.run(route.synchronize())
