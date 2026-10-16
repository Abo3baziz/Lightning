"""Internet catch-up while an experimental profile is open on its owning loop.

Native schedulers supply wake hints. A PC close destroys this runtime and its
unwrapped keys; this module never creates a background password/data-key file.
"""
from __future__ import annotations

import asyncio

from lightning.sync.journal.cloud import (CloudUnavailable, MailboxClient, MailboxExchange,
                                          MailboxPeer, RetryWindow)
from lightning.sync.journal.local import CatchupPaused, LocalChannel
from lightning.sync.journal.membership import Membership
from lightning.sync.journal.owner import public_key
from types import SimpleNamespace

def _public(value):
    return public_key(SimpleNamespace(public_key=value))



class JournalInternet:
    def __init__(self, device, origin, *, client=None):
        self.device = device
        self.trust = Membership(device)
        state = self.trust.state()
        secret = bytes.fromhex(device.store.db.scalar("SELECT value FROM journal_local WHERE name='transport'"))
        self.channel = LocalChannel(device, transport_key=secret, peers={identifier: member["key"] for identifier, member
                                    in state["members"].items() if identifier != device.identity.device_id})
        self.trust.bind(self.channel)
        self.peer = MailboxPeer(self.channel, client or MailboxClient(origin, device))
        self.retry = RetryWindow()
        self.lock = asyncio.Lock()
        self.closed = False

    async def catch_up(self, *, foreground=False):
        if self.closed or self.lock.locked() or (not foreground and not self.retry.ready()):
            return False
        async with self.lock:
            try:
                async with asyncio.timeout(10):
                    await self._membership()
                    if self.device.home:
                        await self.peer.pump(budget=20)
                        await self.peer.pump(budget=20)  # Flush durable replies from this wake-up.
                    else:
                        home_id = next((identifier for identifier, member in self.trust.state()["members"].items()
                                       if _public(member["key"]) == _public(self.device.store.config["home_key"])), None)
                        if home_id is None:
                            from lightning.sync.journal.codec import JournalError
                            raise JournalError("Current home membership is missing; repair authority")
                        await self.channel.synchronize(MailboxExchange(self.peer), home_id=home_id, max_requests=20)
            except (CloudUnavailable, CatchupPaused, OSError, TimeoutError):
                self.retry.result(False)
                return False
            self.retry.result(True)
            return True

    async def _membership(self):
        from lightning.sync.journal.codec import JournalError
        registry = await self.peer.client.call("/authority")
        config = self.device.store.config
        if registry["generation"] != config["generation"]:
            if self.device.store.authority is not None:
                from lightning.sync.journal.authority import AuthorityRegistry
                await AuthorityRegistry(self.peer.client).catch_up(self.device.store.authority,local_device=config["device"])
            raise CloudUnavailable("Authority changed; preserve this copy and verify the successor")
        state = self.trust.state()
        if self.device.home:
            version = registry.get("key_version",1)
            if version > state["version"]:
                raise JournalError("Home membership is older than the registry; explicit repair required")
            while version < state["version"]:
                wire = self.device.store.db.scalar("SELECT value FROM journal_local WHERE name=?",("membership_wire:" + str(version+1),))
                if wire is None:
                    raise JournalError("Membership transition history missing")
                from lightning.sync.journal.codec import unpack
                update = unpack(wire.encode())["body"]
                members = {identifier:_public(member["key"]) for identifier,member in update["members"].items()}
                await self.peer.client.call("/membership",dict(previous=registry["membership"],version=registry["membership"]+1,
                    generation=config["generation"],members=members,key_version=version+1,key_update=wire))
                registry["membership"] += 1
                registry["members"],version = members,version+1
            members = {identifier:_public(member["key"]) for identifier,member in state["members"].items()}
            if registry["members"] != members:
                await self.peer.client.call("/membership",dict(previous=registry["membership"],version=registry["membership"]+1,
                    generation=config["generation"],members=members))
        else:
            for _ in range(16):
                state = self.trust.state()
                if state["version"] >= registry.get("key_version",1):
                    break
                response = await self.peer.client.call("/membership/update",dict(version=state["version"]))
                self.trust.accept(response["update"].encode())
        self.trust.refresh(self.channel)

    async def close(self):
        self.closed = True
        # Caller drains the owning ASGI lifespan before closing the profile.
        async with self.lock:
            self.channel.key = b""
