"""Prefer the paired home's verified LAN link; free cloud is the fallback."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import urlsplit

from lightning.sync.journal.codec import JournalError
from lightning.sync.journal.discovery import discover, local_address
from lightning.sync.journal.local import CatchupPaused, MembershipUpdateRequired, PinnedLocalClient


class LocalFirstSync:
    def __init__(self, device, channel, *, home_id, certificate, endpoints=(), internet=None,
                 discovery=discover, client_factory=PinnedLocalClient):
        self.device, self.channel = device, channel
        self.home_id, self.certificate, self.internet = home_id, certificate, internet
        self.discovery, self.client_factory = discovery, client_factory
        self.lock = asyncio.Lock()
        saved = device.store.db.scalar("SELECT value FROM journal_local WHERE name='local_endpoints'")
        self.endpoints = list(dict.fromkeys([*endpoints, *json.loads(saved or "[]")]))[:4]
        for endpoint in self.endpoints:
            self._validate(endpoint)

    @staticmethod
    def _validate(endpoint):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or not parsed.hostname or not local_address(parsed.hostname)
                or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/exchange"
                or not 1024 <= (parsed.port or 47513) <= 65535):
            raise JournalError("Invalid paired local endpoint")

    def _route(self, name):
        with self.device.store.db.transaction():
            self.device.store.db.execute("INSERT OR REPLACE INTO journal_local VALUES('sync_route',?)", (name,))

    async def _local(self, endpoints):
        for endpoint in endpoints[:4]:
            self._validate(endpoint)
            try:
                request = self.client_factory(endpoint, self.certificate, timeout=1)
                async with asyncio.timeout(3):
                    try:
                        await self.channel.synchronize(request, home_id=self.home_id, max_requests=20)
                    except MembershipUpdateRequired:
                        if not hasattr(self.channel,"membership"):
                            raise
                        control = self.client_factory(endpoint.replace('/exchange','/membership/exchange'),self.certificate,timeout=1)
                        await self.channel.membership.catch_up(control,self.home_id)
                        await self.channel.synchronize(request,home_id=self.home_id,max_requests=20)
            except CatchupPaused:
                # The LAN works; a bounded round paused at its saved cursor.
                self._route("local")
                return True
            except (OSError, TimeoutError):
                continue
            self.endpoints = list(dict.fromkeys([endpoint, *self.endpoints]))[:4]
            with self.device.store.db.transaction():
                self.device.store.db.execute("INSERT OR REPLACE INTO journal_local VALUES('local_endpoints',?)", (json.dumps(self.endpoints),))
            self._route("local")
            return True
        return False

    async def synchronize(self):
        if self.lock.locked():
            return False
        async with self.lock:
            if await self._local(self.endpoints):
                return True
            try:
                found = await self.discovery(self.channel, self.home_id)
            except (OSError, TimeoutError):
                found = []
            if await self._local([endpoint for endpoint in found if endpoint not in self.endpoints]):
                return True
            if self.internet is not None:
                self._route("internet")
                return await self.internet.catch_up(foreground=True)
            self._route("offline")
            return False
