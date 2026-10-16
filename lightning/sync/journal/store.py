"""Durable experimental journal stores, never installed in a production ledger.

Only dummy record kinds are supported. Encryption uses the existing SQLCipher
connection; plaintext requires an explicit laboratory flag. Confirmation, record
state, receipts and stream progress share a single transaction and database.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lightning.database.connection import Database

from .codec import (JournalError, ZERO_HASH, authenticate, canonical, cursor, digest,
                    fields, hash_value, number, origin_id, proposal, seal, unpack, uuid)

SCHEMA = (
    "CREATE TABLE journal_meta (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL, next_seq INTEGER NOT NULL)",
    "CREATE TABLE journal_origins (device TEXT, incarnation TEXT, public_key TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0, revoked INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(device,incarnation))",
    "CREATE TABLE journal_outbox (seq INTEGER PRIMARY KEY, proposal_id TEXT UNIQUE NOT NULL, wire BLOB NOT NULL, decision BLOB, displayed INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE journal_inbox (proposal_id TEXT PRIMARY KEY, device TEXT NOT NULL, incarnation TEXT NOT NULL, seq INTEGER NOT NULL, hash TEXT NOT NULL, wire BLOB NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL, review_token TEXT, UNIQUE(device,incarnation,seq))",
    "CREATE TABLE journal_records (record_id TEXT PRIMARY KEY, groups_json TEXT NOT NULL, tokens_json TEXT NOT NULL, deleted INTEGER NOT NULL)",
    "CREATE TABLE journal_commits (revision INTEGER PRIMARY KEY, hash TEXT UNIQUE NOT NULL, proposal_id TEXT UNIQUE NOT NULL, wire BLOB NOT NULL)",
    "CREATE TABLE journal_reviews (command_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, result BLOB NOT NULL)",
)


class JournalStore:
    """Owns one isolated store and closes it explicitly on the owning thread."""

    @classmethod
    def create(cls, path, *, key, profile, generation, device, incarnation, home_key, origin_key,
               role, dummy=False):
        for identifier in (profile, generation, device, incarnation):
            uuid(identifier)
        if type(role) is not str or role not in {"home", "replica"}:
            raise JournalError("Invalid journal role")
        if key is None and not dummy:
            raise JournalError("Journal storage requires encryption")
        if str(path) != ":memory:":
            target = Path(path)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as error:
                raise JournalError("Never initialize an existing store") from error
            os.close(descriptor)
        db = Database(path, key=key)
        try:
            db.conn.execute("PRAGMA synchronous = FULL")
            with db.transaction():
                for statement in SCHEMA:
                    db.execute(statement)
                config = dict(version=2, profile=profile, generation=generation, device=device,
                              incarnation=incarnation, home_key=home_key, origin_key=origin_key, role=role)
                db.execute("INSERT INTO journal_meta VALUES(1,?,1)", (canonical(config).decode(),))
            return cls(db)
        except BaseException:
            db.close()
            raise

    @classmethod
    def open(cls, path, *, key, dummy=False):
        if key is None and not dummy:
            raise JournalError("Journal storage requires encryption")
        if not Path(path).is_file():
            raise JournalError("Missing journal store; explicit repair required")
        db = Database(path, key=key)
        try:
            db.conn.execute("PRAGMA synchronous = FULL")
            return cls(db)
        except BaseException:
            db.close()
            raise

    def __init__(self, db):
        self.db = db
        try:
            row = db.one("SELECT config,next_seq FROM journal_meta WHERE id=1")
            if row is None:
                raise JournalError("Missing journal identity")
            config = json.loads(row["config"])
            fields(config, ("version", "profile", "generation", "device", "incarnation", "home_key", "origin_key", "role"))
            if config["version"] != 2 or config["role"] not in {"home", "replica"}:
                raise JournalError("Unsupported journal store")
            for field in ("profile", "generation", "device", "incarnation"):
                uuid(config[field])
            from cryptography.hazmat.primitives.asymmetric import ec
            for field in ("home_key", "origin_key"):
                ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(config[field]))
            number(row["next_seq"], minimum=1)
            maximum = db.scalar("SELECT COALESCE(MAX(seq),0) FROM journal_outbox")
            count = db.scalar("SELECT COUNT(*) FROM journal_outbox")
            if row["next_seq"] != maximum + 1 or count != maximum:
                raise JournalError("Uncertain origin counter; repair required")
            self.config = config
        except (db.OperationalError, ValueError, TypeError, KeyError) as error:
            raise JournalError("Invalid journal store; explicit repair required") from error

    def close(self):
        self.db.close()

    def cursor(self):
        row = self.db.one("SELECT revision,hash FROM journal_commits ORDER BY revision DESC LIMIT 1")
        return {"revision": row["revision"], "hash": row["hash"]} if row else {"revision": 0, "hash": ZERO_HASH}

    def record(self, record_id):
        row = self.db.one("SELECT * FROM journal_records WHERE record_id=?", (record_id,))
        if row is None:
            return None
        return dict(record=record_id, groups=json.loads(row["groups_json"]),
                    tokens=json.loads(row["tokens_json"]), deleted=bool(row["deleted"]))

    def fingerprint(self):
        """Dummy-domain contract: sorted UUIDs and normalized groups; no local IDs.

        Tokens/tombstones are protocol metadata, not live ledger state. Production
        domain adapters will need their own reviewed normalization contract.
        """
        import hashlib
        result = hashlib.sha256(b"lightning-dummy-journal-fingerprint-v2\n")
        for row in self.db.all("SELECT record_id,groups_json FROM journal_records WHERE deleted=0 ORDER BY record_id"):
            result.update(canonical({"record": row["record_id"], "groups": json.loads(row["groups_json"])}))
            result.update(b"\n")
        return result.hexdigest()

    def save(self, *, kind, record, groups, bases, signer, dependencies=(), display_zone="Africa/Cairo",
             fault=lambda phase: None):
        """Persist immutable signed bytes and allocate the sequence atomically."""
        with self.db.transaction():
            seq = self.db.scalar("SELECT next_seq FROM journal_meta WHERE id=1")
            body = dict(version=2, type="proposal", profile=self.config["profile"],
                        generation=self.config["generation"],
                        origin=dict(device=self.config["device"], incarnation=self.config["incarnation"], seq=seq),
                        kind=kind, kind_version=1, record=record, groups=groups, bases=bases,
                        dependencies=list(dependencies), cursor=self.cursor(),
                        created_at=datetime.now(timezone.utc).isoformat(), display_zone=display_zone)
            canonical(body)  # Reject unsupported types before semantic validation.
            proposal(body)
            wire = seal(body, signer)
            authenticate(unpack(wire), self.config["origin_key"])
            self.db.execute("INSERT INTO journal_outbox(seq,proposal_id,wire) VALUES(?,?,?)",
                            (seq, origin_id(body["origin"]), wire))
            fault("outbox_inserted")
            self.db.execute("UPDATE journal_meta SET next_seq=? WHERE id=1", (seq + 1,))
            fault("counter_advanced")
        fault("saved")
        return wire

    def pending(self):
        return [bytes(row[0]) for row in self.db.all("SELECT wire FROM journal_outbox WHERE decision IS NULL ORDER BY seq")]

    def mark_displayed(self, proposal_id):
        with self.db.transaction():
            self.db.execute("UPDATE journal_outbox SET displayed=1 WHERE proposal_id=? AND decision IS NOT NULL", (proposal_id,))

    def decisions(self):
        return [dict(row) for row in self.db.all("SELECT proposal_id,decision,displayed FROM journal_outbox WHERE decision IS NOT NULL ORDER BY seq")]

    def _put_record(self, effect):
        self.db.execute("INSERT INTO journal_records VALUES(?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET groups_json=excluded.groups_json,tokens_json=excluded.tokens_json,deleted=excluded.deleted",
                        (effect["record"], canonical(effect["groups"]).decode(),
                         canonical(effect["tokens"]).decode(), int(effect["deleted"])))

    def commits_after(self, confirmed_cursor, *, limit=50):
        cursor(confirmed_cursor)
        if not 1 <= limit <= 50:
            raise JournalError("Invalid batch size")
        self._check_cursor(confirmed_cursor)
        return [bytes(row[0]) for row in self.db.all("SELECT wire FROM journal_commits WHERE revision>? ORDER BY revision LIMIT ?",
                                                   (confirmed_cursor["revision"], limit))]

    def _check_cursor(self, value):
        if value["revision"]:
            known = self.db.scalar("SELECT hash FROM journal_commits WHERE revision=?", (value["revision"],))
            if known != value["hash"]:
                raise JournalError("Unknown checkpoint; verified snapshot required")

    def apply(self, wire, *, fault=lambda phase: None):
        """Apply a signed, typed complete commit; never reinterpret a proposal."""
        if self.config["role"] != "replica":
            raise JournalError("Only replicas replay confirmed effects")
        envelope = unpack(wire)
        authenticate(envelope, self.config["home_key"])
        body = envelope["body"]
        _commit(body)
        self._scope(body)
        with self.db.transaction():
            known = self.db.one("SELECT hash FROM journal_commits WHERE revision=?", (body["revision"],))
            if known:
                if known[0] != digest(body):
                    raise JournalError("Divergent confirmed stream")
                return False
            current = self.cursor()
            if body["revision"] != current["revision"] + 1 or body["previous"] != current["hash"]:
                raise JournalError("Missing or inconsistent predecessor")
            for effect in body["effects"]:
                self._put_record(effect)
            fault("replica_effects")
            if self.fingerprint() != body["fingerprint"]:
                raise JournalError("Ledger fingerprint mismatch; verified snapshot required")
            self.db.execute("INSERT INTO journal_commits VALUES(?,?,?,?)", (body["revision"], digest(body), body["proposal_id"], wire))
            own = self.db.one("SELECT wire FROM journal_outbox WHERE proposal_id=?", (body["proposal_id"],))
            if own:
                if digest(unpack(bytes(own[0]))["body"]) != body["proposal_hash"]:
                    raise JournalError("Decision does not match local proposal")
                self.db.execute("UPDATE journal_outbox SET decision=? WHERE proposal_id=?", (wire, body["proposal_id"]))
            fault("replica_cursor")
        fault("replica_committed")
        return True

    def _scope(self, body):
        if body["profile"] != self.config["profile"] or body["generation"] != self.config["generation"]:
            raise JournalError("Wrong profile or retired authority generation")


def _effect(value):
    fields(value, ("record", "groups", "tokens", "deleted"))
    uuid(value["record"])
    if type(value["deleted"]) is not bool:
        raise JournalError("Invalid deletion effect")
    # Reuse the same group-name and value contract, with a synthetic proposal.
    if type(value["groups"]) is not dict or type(value["tokens"]) is not dict:
        raise JournalError("Invalid effect groups")
    from .codec import GROUP
    if (set(value["groups"]) != set(value["tokens"]) or len(value["groups"]) > 16
            or any(not GROUP.fullmatch(k) for k in value["groups"])):
        raise JournalError("Invalid effect groups")
    for token in value["tokens"].values():
        hash_value(token)
    if value["deleted"] and (value["groups"] or value["tokens"]):
        raise JournalError("A tombstone contains no financial payload")


def _commit(body):
    fields(body, ("version", "type", "profile", "generation", "revision", "previous", "proposal_id",
                  "proposal_hash", "outcome", "reason", "effects", "fingerprint"))
    if type(body["version"]) is not int or body["version"] != 2 or body["type"] != "commit":
        raise JournalError("Unsupported effect schema")
    uuid(body["profile"])
    uuid(body["generation"])
    number(body["revision"], minimum=1)
    for key in ("previous", "proposal_hash", "fingerprint"):
        hash_value(body[key])
    try:
        device, incarnation, seq = body["proposal_id"].split("/")
        if origin_id(dict(device=device, incarnation=incarnation, seq=int(seq))) != body["proposal_id"]:
            raise ValueError
    except (AttributeError, ValueError) as error:
        raise JournalError("Invalid proposal identity") from error
    if type(body["outcome"]) is not str or body["outcome"] not in {"accepted", "rejected"}:
        raise JournalError("Invalid outcome")
    if type(body["reason"]) is not str or body["reason"] not in {"accepted", "cancelled", "dependency-rejected", "missing-record", "deleted", "record-exists", "group-limit", "effect-too-large"}:
        raise JournalError("Unknown decision reason")
    if type(body["effects"]) is not list or len(body["effects"]) > 1:
        raise JournalError("Invalid effects")
    if (body["outcome"] == "accepted") != (len(body["effects"]) == 1):
        raise JournalError("Outcome and effects disagree")
    if (body["reason"] == "accepted") != (body["outcome"] == "accepted"):
        raise JournalError("Outcome and reason disagree")
    for effect in body["effects"]:
        _effect(effect)
