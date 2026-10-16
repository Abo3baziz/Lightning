"""Short-lived pairing bound to both keys, code, matching digits and profile password.

Order is a short-authentication-string comparison: (1) the joining device sends
a signed request proven with the code alone; (2) both screens show the same six
digits and the joiner's user confirms them; (3) only then the joiner sends a
password proof over the pinned connection. Nothing derived from the password
leaves a device before that confirmation. Admission needs the home's own digit
confirmation and a valid password proof, in either order. The data key and
password are never part of a pairing message.
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


def _offer(offer, home_key, now):
    envelope = unpack(offer)
    authenticate(envelope, home_key)
    body = envelope["body"]
    fields(body, ("type", "profile", "generation", "home", "home_key", "nonce", "salt", "expires"))
    if body["type"] != "journal-pairing" or body["home_key"] != home_key or not now() < body["expires"] <= now() + 600:
        raise JournalError("Pairing offer expired or home identity changed")
    return body


def request_pairing(offer, code, identity, incarnation, *, home_key, now=time.time):
    """Phase 1: no password-derived value; the code only proves who may ask."""
    body = _offer(offer, home_key, now)
    uuid(incarnation)
    request = dict(type="journal-pairing-request", offer=digest(body), device=identity.device_id, name=identity.name,
                   key=identity.public_key, incarnation=incarnation)
    request["proof"] = hmac.new(normalize_code(code).encode("ascii"), canonical(request), hashlib.sha256).hexdigest()
    return seal(request, identity.sign), check_digits(canonical(dict(offer=body, request=request)))


def prove_pairing(offer, request, password, identity, *, home_key, now=time.time):
    """Phase 2: call only after the user confirmed the check digits on this device."""
    body = _offer(offer, home_key, now)
    sent = unpack(request)["body"]
    if sent.get("offer") != digest(body) or sent.get("device") != identity.device_id or sent.get("key") != identity.public_key:
        raise JournalError("Pairing request does not match this offer")
    try:
        salt = bytes.fromhex(body["salt"])
        if len(salt) != 16:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise JournalError("Invalid pairing salt") from error
    proof = hmac.new(_password_proof(password, salt), canonical(dict(offer=digest(body), request=digest(sent))), hashlib.sha256).hexdigest()
    return seal(dict(type="journal-pairing-proof", offer=digest(body), request=digest(sent), device=identity.device_id, proof=proof), identity.sign)


class PairingDesk:
    def __init__(self, device, membership, *, clock=time.time, on_admit=None):
        if device.home is None:
            raise JournalError("Pair on the home")
        self.device, self.membership, self.db, self.clock, self.on_admit = device, membership, device.store.db, clock, on_admit

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
        state = dict(offer=offer.decode(), code=code, verifier=_password_proof(password, salt).hex(), attempts=0, proof_attempts=0,
                     request=None, proof=None, confirmed=False)
        with self.db.transaction():
            self.db.execute("INSERT OR REPLACE INTO journal_local VALUES('pairing',?)", (canonical(state).decode(),))
        return offer, code

    def _state(self):
        value = self.db.scalar("SELECT value FROM journal_local WHERE name='pairing'")
        if value is None:
            raise JournalError("Open pairing on the home first")
        state = json.loads(value)
        return state, unpack(state["offer"].encode())["body"]

    def _save(self, state):
        with self.db.transaction():
            self.db.execute("UPDATE journal_local SET value=? WHERE name='pairing'", (canonical(state).decode(),))

    def accept(self, wire):
        """Phase 1: verify the code proof and keep the request. No password is involved yet."""
        state, offer = self._state()
        if self.clock() >= offer["expires"] or state["attempts"] >= 3:
            raise JournalError("Pairing expired; open a new code on the home")
        if state["request"]:
            if state["request"] != wire.decode():
                raise JournalError("Another device is already pairing; stop and open a new code on the home")
            return check_digits(canonical(dict(offer=offer, request=unpack(wire)["body"])))
        # Persist every attempt before interpreting the request, including malformed ones.
        state["attempts"] += 1
        self._save(state)
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
        expected = hmac.new(state["code"].encode("ascii"), canonical(unsigned), hashlib.sha256).hexdigest()
        if type(body["proof"]) is not str or not hmac.compare_digest(body["proof"], expected):
            raise JournalError("Pairing code is wrong")
        state["request"] = wire.decode()
        self._save(state)
        return check_digits(canonical(dict(offer=offer, request=body)))

    def prove(self, wire):
        """Phase 2: the password proof, sent only after the joiner confirmed the digits.

        Returns the membership update once the home has also confirmed, else None.
        """
        state, offer = self._state()
        if not state["request"]:
            raise JournalError("No verified pairing request")
        if self.clock() >= offer["expires"] or state["proof_attempts"] >= 3:
            raise JournalError("Pairing expired; open a new code on the home")
        envelope = unpack(wire)
        body = envelope["body"]
        if state["proof"] and type(body) is dict and state["proof"] == digest(body):
            return None
        state["proof_attempts"] += 1
        self._save(state)
        request = unpack(state["request"].encode())["body"]
        fields(body, ("type", "offer", "request", "device", "proof"))
        authenticate(envelope, request["key"])
        if (body["type"] != "journal-pairing-proof" or body["offer"] != digest(offer) or body["request"] != digest(request)
                or body["device"] != request["device"]):
            raise JournalError("Pairing transcript changed")
        expected = hmac.new(bytes.fromhex(state["verifier"]), canonical(dict(offer=body["offer"], request=body["request"])), hashlib.sha256).hexdigest()
        if type(body["proof"]) is not str or not hmac.compare_digest(body["proof"], expected):
            raise JournalError("Profile password is wrong")
        state["proof"] = digest(body)
        self._save(state)
        return self._admit(state) if state["confirmed"] else None

    def confirm(self, digits):
        """The home owner's comparison. Returns the membership update once the password proof exists, else None."""
        self.device.store.require_confirmation_authority()
        state, offer = self._state()
        if not state.get("request"):
            raise JournalError("No verified pairing request")
        body = unpack(state["request"].encode())["body"]
        expected = check_digits(canonical(dict(offer=offer, request=body)))
        if self.clock() >= offer["expires"] or type(digits) is not str or not hmac.compare_digest(digits, expected):
            raise JournalError("Check that both devices show the same six digits")
        state["confirmed"] = True
        self._save(state)
        return self._admit(state) if state["proof"] else None

    def _admit(self, state):
        self.device.store.require_confirmation_authority()
        body = unpack(state["request"].encode())["body"]
        members = dict(self.membership.state()["members"])
        if body["device"] in members:
            raise JournalError("This device is already paired; use its saved identity")
        members[body["device"]] = dict(key=body["key"], incarnation=body["incarnation"])
        with self.db.transaction():
            result = self.membership.rotate(members)
            self.db.execute("DELETE FROM journal_local WHERE name='pairing'")
            if self.on_admit:
                self.on_admit(state["request"], result)
        return result
