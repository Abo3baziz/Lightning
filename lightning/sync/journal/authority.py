"""Durable fencing and explicit owner-authorized generation transitions.

The independent control file is never in a profile backup. Losing it blocks
confirmation; profile restore cannot rewind the highest observed generation.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from lightning.sync.identity import verify_signature
from .codec import (JournalError, authenticate, canonical, cursor, digest, fields,
                    hash_value, number, seal, unpack, uuid)


def transition(body):
    fields(body, ("profile", "previous", "generation", "home", "home_key", "owner_key", "version", "mode", "nonce", "cutoff"))
    for key in ("profile", "previous", "generation", "home"):
        uuid(body[key])
    number(body["version"], minimum=2)
    hash_value(body["nonce"])
    cursor(body["cutoff"])
    if body["previous"] == body["generation"] or body["mode"] not in ("move", "recover", "rotate-owner"):
        raise JournalError("Invalid authority transition")
    from cryptography.hazmat.primitives.asymmetric import ec
    for key in ("home_key", "owner_key"):
        try:
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(body[key]))
        except (ValueError, TypeError) as error:
            raise JournalError("Invalid authority public key") from error


class AuthorityMemory:
    def __init__(self, path, *, profile):
        self.path, self.profile = Path(path), profile
        if not self.path.is_file() or self.path.is_symlink():
            raise JournalError("Authority memory is missing; explicit repair required")
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self._confirm_depth = 0
        self.db.execute("PRAGMA synchronous=FULL")
        try:
            self.state()
        except BaseException:
            self.db.close()
            raise

    @classmethod
    def enroll(cls, path, wire):
        envelope = unpack(wire)
        body = envelope["body"]
        fields(body, ("type", "version", "profile", "generation", "home", "home_key", "owner_key"))
        if body["type"] != "authority-enrollment" or body["version"] != 1:
            raise JournalError("Invalid authority enrollment")
        for key in ("profile", "generation", "home"):
            uuid(body[key])
        authenticate(envelope, body["owner_key"])
        path = Path(path)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        db = sqlite3.connect(path, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE authority(id INTEGER PRIMARY KEY CHECK(id=1),document TEXT NOT NULL)")
            db.execute("CREATE TABLE certificates(version INTEGER PRIMARY KEY,wire BLOB NOT NULL)")
            state = body | dict(phase="active", cutoff=dict(revision=0, hash="0" * 64), predecessor=None)
            db.execute("INSERT INTO authority VALUES(1,?)", (canonical(state).decode(),))
            db.execute("INSERT INTO certificates VALUES(1,?)", (wire,))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return cls(path, profile=body["profile"])

    def close(self):
        self.db.close()

    def state(self):
        try:
            row = self.db.execute("SELECT document FROM authority WHERE id=1").fetchone()
            if row is None:
                raise ValueError
            value = json.loads(row[0])
            if value["profile"] != self.profile or value["phase"] not in ("active", "frozen", "retired", "candidate", "prepared"):
                raise ValueError
            number(value["version"], minimum=1)
            uuid(value["generation"])
            cursor(value["cutoff"])
            return value
        except (sqlite3.Error, ValueError, KeyError, TypeError) as error:
            raise JournalError("Authority memory is damaged; confirmation blocked") from error

    def _change(self, apply):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            value = self.state()
            result = apply(value)
            self.db.execute("UPDATE authority SET document=? WHERE id=1", (canonical(value).decode(),))
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def bind(self, store):
        state = self.state()
        if state["profile"] != store.config["profile"]:
            raise JournalError("Authority memory belongs to another profile")
        store.authority = self
        with store.db.transaction():
            store.db.execute("INSERT OR REPLACE INTO journal_local VALUES('authority_enrolled','1')")

    def can_confirm(self, store):
        state = self.state()
        return (state["phase"] == "active" and state["generation"] == store.config["generation"]
                and state["home"] == store.config["device"] and state["home_key"] == store.config["home_key"])

    @contextmanager
    def confirming(self, store):
        """Serialize freeze/retirement with the complete financial commit."""
        outer = self._confirm_depth == 0
        if outer:
            self.db.execute("BEGIN IMMEDIATE")
        try:
            if not self.can_confirm(store):
                raise JournalError("Confirmation is frozen or this home is retired")
            self._confirm_depth += 1
            try:
                yield
            finally:
                self._confirm_depth -= 1
            if outer:
                self.db.execute("COMMIT")
        except BaseException:
            if outer and self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def freeze(self, store):
        if not self.can_confirm(store):
            raise JournalError("Only the active home can freeze")
        def apply(state):
            if state["phase"] != "active" or state["generation"] != store.config["generation"]:
                raise JournalError("The authority already changed")
            state["phase"], state["cutoff"] = "frozen", store.cursor()
        self._change(apply)
        return self.state()["cutoff"]

    def verify_transition(self, wire):
        envelope = unpack(wire)
        transition(envelope["body"])
        state = self.state()
        authenticate(envelope, state["owner_key"])
        body = envelope["body"]
        if body["profile"] != self.profile or body["previous"] != state["generation"] or body["version"] != state["version"] + 1:
            raise JournalError("Stale or competing authority transition")
        return body

    def prepare(self, store, wire, signer):
        body = self.verify_transition(wire)
        if (body["home"] != store.config["device"] or store.cursor() != body["cutoff"]
                or store.config["generation"] != body["previous"]):
            raise JournalError("Target must install and verify the final checkpoint before preparing")
        receipt = dict(type="authority-prepared", transition=digest(body), cursor=store.cursor(), fingerprint=store.fingerprint())
        result = seal(receipt, signer)
        def apply(state):
            if state["phase"] not in ("active", "prepared"):
                raise JournalError("Target is not available to prepare")
            state["phase"], state["prepared"] = "prepared", digest(body)
        self._change(apply)
        return result

    def retire(self, store, wire, prepared, signer):
        body = self.verify_transition(wire)
        state = self.state()
        if state["phase"] != "frozen" or state["home"] != store.config["device"] or state["cutoff"] != body["cutoff"]:
            raise JournalError("Freeze the home at the final checkpoint before retirement")
        envelope = unpack(prepared)
        authenticate(envelope, body["home_key"])
        fields(envelope["body"], ("type", "transition", "cursor", "fingerprint"))
        expected = dict(type="authority-prepared", transition=digest(body), cursor=store.cursor(), fingerprint=store.fingerprint())
        if envelope["body"] != expected:
            raise JournalError("Target prepared another checkpoint")
        def apply(current):
            if current["phase"] != "frozen":
                raise JournalError("Home was already retired")
            current["phase"], current["retirement"] = "retired", digest(body)
        self._change(apply)  # Retirement is durable before its signature escapes.
        return seal(dict(type="authority-retired", transition=digest(body), prepared=digest(envelope["body"])), signer)

    def observe(self, wire, *, local_device):
        """Pin a successor before opening its profile; no timeout may activate it."""
        body = self.verify_transition(wire)
        def apply(state):
            if state["generation"] != body["previous"]:
                raise JournalError("A newer authority was already observed")
            self.db.execute("INSERT INTO certificates VALUES(?,?)", (body["version"], wire))
            state.update(body)
            state["phase"] = "candidate" if body["home"] == local_device else "retired"
            state["predecessor"] = body["previous"]
        self._change(apply)

    def activate_move(self, store, wire, prepared, retired, *, old_home_key):
        body = self.verify_transition(wire)
        state = self.state()
        if state["phase"] != "prepared" or state.get("prepared") != digest(body) or body["mode"] != "move":
            raise JournalError("Target has not prepared this move")
        confirmation = unpack(retired)
        authenticate(confirmation, old_home_key)
        if confirmation["body"] != dict(type="authority-retired", transition=digest(body), prepared=digest(unpack(prepared)["body"])):
            raise JournalError("No matching durable old-home retirement")
        self.observe(wire, local_device=store.config["device"])
        self._activate(store, body)

    async def recover(self, store, wire, registry):
        """Obtain a live CAS result from the configured authenticated registry."""
        body = self.verify_transition(wire)
        if body["mode"] != "recover" or body["home"] != store.config["device"] or body["cutoff"] != store.cursor():
            raise JournalError("Recovery requires the verified surviving prefix")
        await registry.publish(wire)
        self.observe(wire, local_device=store.config["device"])
        self._activate(store, body)

    def _activate(self, store, body):
        if self.state()["phase"] != "candidate" or body["home"] != store.config["device"]:
            raise JournalError("Only the pinned target can activate")
        config = dict(store.config, generation=body["generation"], home_key=body["home_key"], role="home")
        with store.db.transaction():
            store.db.execute("UPDATE journal_meta SET config=? WHERE id=1", (canonical(config).decode(),))
        store.config = config
        # Crash before this last control commit leaves a blocked candidate.
        self._change(lambda state: state.update(phase="active"))

    def admits_original(self, body):
        """Allow signed original proposals from an explicitly retired branch."""
        if body["profile"] != self.profile:
            return False
        for (wire,) in self.db.execute("SELECT wire FROM certificates WHERE version>1"):
            certificate = unpack(bytes(wire))["body"]
            if certificate["previous"] == body["generation"]:
                return True
        return False


def transfer_home_state(source, target):
    """Copy final inbox/receipts only after financial snapshot verification.

    Device-local queues and counters remain on their original devices.
    """
    if source.authority.state()["phase"] != "frozen" or source.cursor() != target.cursor() or source.fingerprint() != target.fingerprint():
        raise JournalError("A frozen identical checkpoint is required for handover")
    with target.db.transaction():
        for table in ("journal_origins", "journal_inbox", "journal_reviews"):
            target.db.execute(f"DELETE FROM {table}")
            for row in source.db.all(f"SELECT * FROM {table}"):
                target.db.execute(f"INSERT INTO {table} VALUES({','.join('?' for _ in row)})", tuple(row))


class AuthorityRegistry:
    """Online registry over MailboxClient's configured TLS origin.

    Publication uses an owner signature, independently of device admission.
    A lost reply is reconciled by reading the durable winning certificate.
    """
    def __init__(self, client):
        self.client = client

    async def publish(self, wire):
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        from .cloud import CloudUnavailable
        envelope = unpack(wire)
        body = envelope["body"]
        transition(body)
        r, s = decode_dss_signature(bytes.fromhex(envelope["signature"]))
        request = dict(body=body, signature=(r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex())
        try:
            await self.client.call("/authority/transition", request)
        except CloudUnavailable:
            # A timeout/409 may mean another attempt won; never assume our own.
            pass
        current = await self.client.call("/authority")
        if (current.get("generation") != body["generation"] or current.get("version") != body["version"]
                or current.get("certificate") != request):
            raise JournalError("Registry selected another successor; preserve this copy")
        return current
