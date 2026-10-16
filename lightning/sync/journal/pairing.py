"""Short-lived pairing proof bound to both keys, code and profile password.

Admission is a separate local-home confirmation after matching six digits.
The data key and password are never part of a pairing request or response.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time

from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from lightning.security.keys import unwrap_key, _password_bytes
from lightning.sync.identity import check_digits
from .codec import JournalError, authenticate, canonical, digest, fields, seal, unpack, uuid


def _password_proof(password, salt):
    return Argon2id(salt=salt, length=32, iterations=4, lanes=4, memory_cost=131072).derive(_password_bytes(password))


def normalize_code(value):
    if type(value) is not str or len(value) > 32:
        raise JournalError("Enter the six-digit number shown on the home")
    value = value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2))
    code = "".join(char for char in value if char not in " -\t\r\n")
    if len(code) != 6 or any(char not in "0123456789" for char in code):
        raise JournalError("Enter the six-digit number shown on the home")
    return code


def request_pairing(offer, code, password, identity, incarnation, *, home_key, now=time.time):
    envelope = unpack(offer)
    authenticate(envelope, home_key)
    body = envelope["body"]
    fields(body, ("type", "profile", "generation", "home", "home_key", "nonce", "salt", "expires"))
    if body["type"] != "journal-pairing" or body["home_key"] != home_key or not now() < body["expires"] <= now() + 600:
        raise JournalError("Pairing offer expired or home identity changed")
    uuid(incarnation)
    try:
        salt = bytes.fromhex(body["salt"])
        if len(salt) != 16:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise JournalError("Invalid pairing salt") from error
    request = dict(type="journal-pairing-request", offer=digest(body), device=identity.device_id, name=identity.name,
                   key=identity.public_key, incarnation=incarnation)
    secret = _password_proof(password, salt)
    request["proof"] = hmac.new(secret, normalize_code(code).encode("ascii") + canonical(request), hashlib.sha256).hexdigest()
    wire = seal(request, identity.sign)
    return wire, check_digits(canonical(dict(offer=body, request=request)))


class PairingDesk:
    def __init__(self, device, membership, *, clock=time.time):
        if device.home is None:
            raise JournalError("Pair on the home")
        self.device, self.membership, self.db, self.clock = device, membership, device.store.db, clock

    def begin(self, key_file, password):
        self.device.store.require_confirmation_authority()
        if not hmac.compare_digest(unwrap_key(key_file, password), self.db.copy_key()):
            raise JournalError("Password belongs to a different profile")
        salt, code = os.urandom(16), f"{secrets.randbelow(1000000):06d}"
        config = self.device.store.config
        body = dict(type="journal-pairing", profile=config["profile"], generation=config["generation"],
                    home=config["device"], home_key=config["home_key"], nonce=os.urandom(32).hex(),
                    salt=salt.hex(), expires=int(self.clock()) + 600)
        offer = seal(body, self.device.identity.sign)
        # Temporary proof verifier lives only in the encrypted profile and expires.
        state = dict(offer=offer.decode(), code=code, verifier=_password_proof(password, salt).hex(), attempts=0, request=None)
        with self.db.transaction():
            self.db.execute("INSERT OR REPLACE INTO journal_local VALUES('pairing',?)", (canonical(state).decode(),))
        return offer, code

    def accept(self, wire):
        value = self.db.scalar("SELECT value FROM journal_local WHERE name='pairing'")
        if value is None:
            raise JournalError("Open pairing on the home first")
        state = json.loads(value)
        offer = unpack(state["offer"].encode())["body"]
        if self.clock() >= offer["expires"] or state["attempts"] >= 3:
            raise JournalError("Pairing expired; open a new code on the home")
        # Persist every attempt before interpreting the request, including malformed ones.
        with self.db.transaction():
            state["attempts"] += 1
            self.db.execute("UPDATE journal_local SET value=? WHERE name='pairing'", (canonical(state).decode(),))
        envelope = unpack(wire)
        body = envelope["body"]
        fields(body, ("type", "offer", "device", "name", "key", "incarnation", "proof"))
        if type(body["name"]) is not str or not 1 <= len(body["name"].strip()) <= 60:
            raise JournalError("Invalid nearby device name")
        uuid(body["device"])
        uuid(body["incarnation"])
        authenticate(envelope, body["key"])
        if body["type"] != "journal-pairing-request" or body["offer"] != digest(offer):
            raise JournalError("Pairing transcript changed")
        unsigned = {key: value for key, value in body.items() if key != "proof"}
        expected = hmac.new(bytes.fromhex(state["verifier"]), state["code"].encode("ascii") + canonical(unsigned), hashlib.sha256).hexdigest()
        if type(body["proof"]) is not str or not hmac.compare_digest(body["proof"], expected):
            raise JournalError("Pairing code or profile password is wrong")
        state["request"] = wire.decode()
        with self.db.transaction():
            self.db.execute("UPDATE journal_local SET value=? WHERE name='pairing'", (canonical(state).decode(),))
        return check_digits(canonical(dict(offer=offer, request=body)))

    def confirm(self, digits):
        self.device.store.require_confirmation_authority()
        state = json.loads(self.db.scalar("SELECT value FROM journal_local WHERE name='pairing'") or "{}")
        if not state.get("request"):
            raise JournalError("No verified pairing request")
        offer = unpack(state["offer"].encode())["body"]
        body = unpack(state["request"].encode())["body"]
        expected = check_digits(canonical(dict(offer=offer, request=body)))
        if self.clock() >= offer["expires"] or type(digits) is not str or not hmac.compare_digest(digits, expected):
            raise JournalError("Check that both devices show the same six digits")
        members = dict(self.membership.state()["members"])
        if body["device"] in members:
            raise JournalError("This device is already paired; use its saved identity")
        members[body["device"]] = dict(key=body["key"], incarnation=body["incarnation"])
        with self.db.transaction():
            result = self.membership.rotate(members)
            self.db.execute("DELETE FROM journal_local WHERE name='pairing'")
        return result
