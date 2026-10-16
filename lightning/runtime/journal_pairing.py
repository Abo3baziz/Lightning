"""Nearby-device pairing flow for explicit compatible dummy profiles.

User-visible choices use names and opaque candidate IDs, never typed endpoints.
Native first-profile snapshot enrollment remains a separate cutover gate.
"""
from __future__ import annotations

import json
import time

from lightning.sync.journal.codec import JournalError, authenticate, canonical, digest, fields, hash_value, seal, unpack, uuid
from lightning.sync.journal.discovery import nearby_devices
from lightning.sync.journal.local import PinnedLocalClient
from lightning.sync.journal.membership import Membership
from lightning.sync.journal.pairing import PairingDesk, request_pairing


class NearbyPairing:
    def __init__(self, device, *, key_document=None, search=nearby_devices, client_factory=PinnedLocalClient):
        self.device, self.db = device, device.store.db
        self.membership = Membership(device)
        self.keys, self.search, self.client_factory = key_document, search, client_factory
        self.desk = PairingDesk(device,self.membership) if device.home else None

    def _value(self, name, default=None):
        value = self.db.scalar("SELECT value FROM journal_local WHERE name=?", (name,))
        return json.loads(value) if value else default

    def _save(self, name, value):
        self.db.execute("INSERT OR REPLACE INTO journal_local VALUES(?,?)", (name,json.dumps(value,separators=(",",":"))))

    def screen(self):
        names = self._value("paired_names",{})
        state = self._value("pairing",{})
        if state and unpack(state["offer"].encode())["body"]["expires"] <= time.time():
            state = {}
        request = unpack(state["request"].encode())["body"] if state.get("request") else None
        from lightning.sync.identity import check_digits
        return dict(enabled=True, paired=self.device.identity.device_id in self.membership.state()["members"], code=state.get("code"), request_name=request["name"] if request else None,
                    digits=check_digits(canonical(dict(offer=unpack(state["offer"].encode())["body"],request=request))) if request else None,
                    members=[names.get(identifier,"Paired device") for identifier in self.membership.state()["members"]
                             if identifier != self.device.identity.device_id],
                    nearby=[dict(id=identifier,name=value["name"]) for identifier,value in self._value("nearby",{}).items()],
                    pending=self._value("pairing_client",{}).get("digits"))

    def begin(self, password):
        if self.desk is None or self.keys is None:
            raise JournalError("Open pairing on the home")
        self.desk.begin(self.keys(),password)

    def stop(self):
        self.db.execute("DELETE FROM journal_local WHERE name='pairing'")

    def advertise(self, nonce, port):
        state = self._value("pairing",{})
        if not state or state["attempts"] >= 3 or unpack(state["offer"].encode())["body"]["expires"] <= time.time():
            return None
        return seal(dict(type="journal-nearby-home", nonce=nonce, name=self.device.identity.name,
                         home=self.device.identity.device_id, offer=state["offer"], port=port,
                         certificate=self.device.identity.cert_path.read_text()),self.device.identity.sign)

    async def find(self):
        found = await self.search(self.device.identity)
        # Discovery advertises identity only. Code/password proof and matching
        # digits are still required before any new device is admitted.
        candidates = {digest(dict(home=item["home"],offer=item["offer"])):item for item in found}
        with self.db.transaction():
            self._save("nearby",candidates)
        return len(candidates)

    async def join(self, identifier, code, password):
        candidate = self._value("nearby",{}).get(identifier)
        if candidate is None:
            raise JournalError("Search for nearby devices again")
        offer = unpack(candidate["offer"].encode())["body"]
        config = self.device.store.config
        from lightning.sync.journal.owner import public_key
        from types import SimpleNamespace
        if (offer["profile"] != config["profile"] or offer["generation"] != config["generation"]
                or public_key(SimpleNamespace(public_key=offer["home_key"])) != public_key(SimpleNamespace(public_key=config["home_key"]))):
            raise JournalError("This preview joins compatible dummy replicas; a new profile requires snapshot enrollment")
        if self.device.store.pending():
            raise JournalError("Sync existing pending work before pairing another connection")
        wire,digits = request_pairing(candidate["offer"].encode(),code,password,self.device.identity,config["incarnation"],home_key=offer["home_key"])
        request = self.client_factory(candidate["endpoint"],candidate["certificate"],timeout=5)
        answer = unpack(await request(wire))
        authenticate(answer,config["home_key"])
        if answer["body"] != dict(type="pairing-wait",request=digest(unpack(wire)["body"])):
            raise JournalError("Pairing reply changed; reopen pairing on the home")
        with self.db.transaction():
            self._save("pairing_client",dict(candidate=candidate,request=wire.decode(),digits=digits))

    def confirm(self, digits):
        state = self._value("pairing",{})
        if self.desk is None or not state.get("request"):
            raise JournalError("No device is waiting for approval")
        request = unpack(state["request"].encode())["body"]
        with self.db.transaction():
            membership = self.desk.confirm(digits)
            self._save("pairing_result:" + digest(request), dict(request=state["request"],membership=membership.decode(),expires=int(time.time())+600))
            names = self._value("paired_names",{})
            names[request["device"]] = request["name"]
            self._save("paired_names",names)

    def exchange(self, wire):
        if self.desk is None or len(wire) > 4096:
            raise JournalError("Pairing request refused")
        envelope = unpack(wire)
        body = envelope["body"]
        if type(body) is not dict:
            raise JournalError("Invalid pairing message")
        if body.get("type") == "journal-pairing-request":
            self.desk.accept(wire)
            return seal(dict(type="pairing-wait",request=digest(body)),self.device.identity.sign)
        fields(body,("type","request","device"))
        hash_value(body["request"])
        uuid(body["device"])
        saved = self._value("pairing_result:" + body["request"],{})
        if body["type"] != "journal-pairing-status" or not saved or saved["expires"] < time.time():
            raise JournalError("Pairing approval is not available yet")
        original = unpack(saved["request"].encode())["body"]
        authenticate(envelope,original["key"])
        if body["device"] != original["device"]:
            raise JournalError("Pairing approval belongs to another device")
        return seal(dict(type="pairing-approved",request=body["request"],membership=saved["membership"]),self.device.identity.sign)

    async def finish(self):
        state = self._value("pairing_client",{})
        if not state:
            raise JournalError("Choose a nearby device and enter its number first")
        identifier = digest(unpack(state["request"].encode())["body"])
        wire = seal(dict(type="journal-pairing-status",request=identifier,device=self.device.identity.device_id),self.device.identity.sign)
        candidate = state["candidate"]
        request = self.client_factory(candidate["endpoint"],candidate["certificate"],timeout=5)
        answer = unpack(await request(wire))
        authenticate(answer,self.device.store.config["home_key"])
        if answer["body"].get("type") != "pairing-approved" or answer["body"].get("request") != identifier:
            raise JournalError("Home has not approved this connection")
        with self.db.transaction():
            self.membership.accept(answer["body"]["membership"].encode(),initial=True)
            self._save("local_endpoints",[candidate["endpoint"].replace('/pairing/exchange','/exchange')])
            names = self._value("paired_names",{})
            names[candidate["home"]] = candidate["name"]
            self._save("paired_names",names)
            self.db.execute("DELETE FROM journal_local WHERE name='pairing_client'")
