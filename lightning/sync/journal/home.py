"""Single-home confirmation and a separate idempotent review lane for dummy data."""
from __future__ import annotations

from .codec import (JournalError, authenticate, canonical, digest, origin_id,
                    proposal, seal, unpack, uuid)
from .store import JournalStore, _commit

MAX_GAP = 256
MAX_STAGED = 1024


class JournalHome:
    def __init__(self, store: JournalStore, signer, *, fault=lambda phase: None):
        if store.config["role"] != "home":
            raise JournalError("Only the home confirms proposals")
        self.store, self.db, self.signer, self.fault = store, store.db, signer, fault

    def approve_origin(self, device, incarnation, public_key):
        """Laboratory enrollment only; production pairing must authenticate this."""
        from cryptography.hazmat.primitives.asymmetric import ec
        uuid(device)
        uuid(incarnation)
        try:
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(public_key))
        except (ValueError, TypeError) as error:
            raise JournalError("Invalid origin public key") from error
        with self.db.transaction():
            existing = self.db.one("SELECT public_key,revoked FROM journal_origins WHERE device=? AND incarnation=?",
                                   (device, incarnation))
            if existing:
                if existing["public_key"] != public_key or existing["revoked"]:
                    raise JournalError("Origin identity cannot be replaced or revived")
                return
            self.db.execute("INSERT INTO journal_origins(device,incarnation,public_key) VALUES(?,?,?)",
                            (device, incarnation, public_key))

    def revoke_origin(self, device, incarnation):
        """Local admission gate only, not production transport-key revocation."""
        with self.db.transaction():
            self.db.execute("UPDATE journal_origins SET revoked=1 WHERE device=? AND incarnation=?", (device, incarnation))

    def receive(self, wire):
        envelope = unpack(wire)
        body = envelope["body"]
        # Only inspect bounded routing identity before authenticating financial contents.
        if type(body) is not dict or type(body.get("origin")) is not dict:
            raise JournalError("Missing origin")
        identity = body["origin"]
        identifier = origin_id(identity)
        with self.db.transaction():
            member = self.db.one("SELECT * FROM journal_origins WHERE device=? AND incarnation=?",
                                 (identity["device"], identity["incarnation"]))
            if member is None or member["revoked"]:
                raise JournalError("Origin is not currently trusted")
            authenticate(envelope, member["public_key"])
            proposal(body)
            self.store._scope(body)
            self.store._check_cursor(body["cursor"])
            payload_hash = digest(body)
            known = self.db.one("SELECT hash,status FROM journal_inbox WHERE proposal_id=?", (identifier,))
            if known:
                if known["hash"] != payload_hash:
                    raise JournalError("Proposal identity reused with different content")
                return known["status"]
            if identity["seq"] <= member["progress"]:
                raise JournalError("Missing receipt below origin progress; repair required")
            if identity["seq"] > member["progress"] + MAX_GAP:
                raise JournalError("Sequence gap exceeds staging window")
            if self.db.scalar("SELECT COUNT(*) FROM journal_inbox WHERE status IN ('staged','review')") >= MAX_STAGED:
                raise JournalError("Staging capacity reached; retain the edit on its origin")
            self.db.execute("INSERT INTO journal_inbox VALUES(?,?,?,?,?,?,'staged','queued',NULL)",
                            (identifier, identity["device"], identity["incarnation"], identity["seq"], payload_hash, wire))
            self.fault("inbox_inserted")
        self.fault("inbox_committed")
        return "staged"

    def process(self):
        """Drain eligible work; a review blocks its origin, never other origins."""
        committed = []
        while True:
            progressed = False
            members = self.db.all("SELECT * FROM journal_origins WHERE revoked=0 ORDER BY device,incarnation")
            for member in members:
                with self.db.transaction():
                    row = self.db.one("SELECT * FROM journal_inbox WHERE device=? AND incarnation=? AND seq=?",
                                      (member["device"], member["incarnation"], member["progress"] + 1))
                    if row is None or row["status"] != "staged":
                        continue
                    body = unpack(bytes(row["wire"]))["body"]
                    result = self._consider(body)
                    if result[0] == "wait":
                        continue
                    if result[0] == "review":
                        self.db.execute("UPDATE journal_inbox SET status='review',reason='conflict',review_token=? WHERE proposal_id=?",
                                        (self._review_token(row), row["proposal_id"]))
                        continue
                    wire = self._finish(row, *result)
                # Nothing escapes the transaction before it is durably committed.
                self.fault("decision_committed")
                committed.append(wire)
                progressed = True
            if not progressed:
                return committed

    def _consider(self, body, *, force=False):
        dependencies = []
        for dependency in body["dependencies"]:
            row = self.db.one("SELECT status FROM journal_inbox WHERE proposal_id=?", (origin_id(dependency),))
            if row is not None and row[0] == "rejected":
                return "rejected", "dependency-rejected", []
            if row is None or row[0] != "accepted":
                return "wait", "dependency", []
            commit = self._decision(origin_id(dependency))
            dependencies.extend(unpack(commit)["body"]["effects"])
        current = self.store.record(body["record"])
        if current and current["deleted"]:
            return "rejected", "deleted", []
        if body["kind"] == "dummy.add":
            if current:
                return "rejected", "record-exists", []
            if any(value is not None for value in body["bases"].values()):
                raise JournalError("An addition cannot have existing base tokens")
            groups, tokens = {}, {}
        else:
            if current is None:
                return "rejected", "missing-record", []
            groups, tokens = dict(current["groups"]), dict(current["tokens"])
            bases = dict(body["bases"])
            for group, base in bases.items():
                if base is None:
                    inherited = {effect["tokens"][group] for effect in dependencies
                                 if effect["record"] == body["record"] and group in effect["tokens"]}
                    if len(inherited) > 1:
                        return "review", "conflict", []
                    if inherited:
                        bases[group] = inherited.pop()
            if not force:
                if body["kind"] == "dummy.delete" and set(bases) != set(tokens):
                    return "review", "conflict", []
                if any(tokens.get(group) != token for group, token in bases.items()):
                    return "review", "conflict", []
        if body["kind"] == "dummy.delete":
            effect = dict(record=body["record"], groups={}, tokens={}, deleted=True)
        else:
            groups.update(body["groups"])
            for group in body["groups"]:
                tokens[group] = digest(dict(proposal=digest(body), group=group))
            effect = dict(record=body["record"], groups=groups, tokens=tokens, deleted=False)
        if len(effect["groups"]) > 16:
            return "rejected", "group-limit", []
        if len(canonical(effect)) > 48 * 1024:
            return "rejected", "effect-too-large", []
        return "accepted", "accepted", [effect]

    def _finish(self, row, outcome, reason, effects):
        if outcome not in {"accepted", "rejected"}:
            raise JournalError("Only terminal decisions advance origin progress")
        for effect in effects:
            self.store._put_record(effect)
        self.fault("home_effects")
        current = self.store.cursor()
        body = dict(version=2, type="commit", profile=self.store.config["profile"],
                    generation=self.store.config["generation"], revision=current["revision"] + 1,
                    previous=current["hash"], proposal_id=row["proposal_id"], proposal_hash=row["hash"],
                    outcome=outcome, reason=reason, effects=effects, fingerprint=self.store.fingerprint())
        _commit(body)
        wire = seal(body, self.signer)
        authenticate(unpack(wire), self.store.config["home_key"])
        self.db.execute("INSERT INTO journal_commits VALUES(?,?,?,?)", (body["revision"], digest(body), body["proposal_id"], wire))
        self.db.execute("UPDATE journal_inbox SET status=?,reason=?,review_token=NULL WHERE proposal_id=?",
                        (outcome, reason, row["proposal_id"]))
        self.db.execute("UPDATE journal_origins SET progress=? WHERE device=? AND incarnation=?",
                        (row["seq"], row["device"], row["incarnation"]))
        own = self.db.one("SELECT wire FROM journal_outbox WHERE proposal_id=?", (row["proposal_id"],))
        if own:
            if digest(unpack(bytes(own[0]))["body"]) != row["hash"]:
                raise JournalError("Decision does not match local proposal")
            self.db.execute("UPDATE journal_outbox SET decision=? WHERE proposal_id=?", (wire, row["proposal_id"]))
        self.fault("home_receipt")
        return wire

    def _decision(self, proposal_id):
        # Receipt payloads are retained in this milestone; no compaction yet.
        row = self.db.one("SELECT wire FROM journal_commits WHERE proposal_id=?", (proposal_id,))
        if row:
            return bytes(row[0])
        raise JournalError("Missing committed receipt; repair required")

    def status(self, proposal_id):
        row = self.db.one("SELECT status,reason FROM journal_inbox WHERE proposal_id=?", (proposal_id,))
        return dict(row) if row else None

    def decision(self, proposal_id):
        """Return the original signed terminal decision, including after restart."""
        state = self.status(proposal_id)
        if state is None or state["status"] not in {"accepted", "rejected"}:
            return None
        return self._decision(proposal_id)

    def _review_token(self, row):
        body = unpack(bytes(row["wire"]))["body"]
        return digest(dict(proposal=row["hash"], current=self.store.record(body["record"])))

    def review_state(self, proposal_id):
        with self.db.transaction():
            row = self.db.one("SELECT * FROM journal_inbox WHERE proposal_id=? AND status='review'", (proposal_id,))
            if row is None:
                raise JournalError("Proposal is not waiting for review")
            body = unpack(bytes(row["wire"]))["body"]
            token = self._review_token(row)
            self.db.execute("UPDATE journal_inbox SET review_token=? WHERE proposal_id=?", (token, proposal_id))
            return dict(proposal_id=proposal_id, token=token, proposed=body,
                        current=self.store.record(body["record"]))

    def review(self, *, command_id, proposal_id, token, choice):
        """Called only by the local home in the lab; not a network control endpoint."""
        uuid(command_id)
        if type(choice) is not str or choice not in {"apply", "reject"}:
            raise JournalError("Invalid review choice")
        request_hash = digest(dict(proposal_id=proposal_id, token=token, choice=choice))
        with self.db.transaction():
            known = self.db.one("SELECT request_hash,result FROM journal_reviews WHERE command_id=?", (command_id,))
            if known:
                if request_hash != known["request_hash"]:
                    raise JournalError("Review identity reused with different content")
                return bytes(known["result"])
            row = self.db.one("SELECT * FROM journal_inbox WHERE proposal_id=? AND status='review'", (proposal_id,))
            if row is None or token != self._review_token(row):
                raise JournalError("Review changed; refresh before choosing")
            member = self.db.one("SELECT revoked FROM journal_origins WHERE device=? AND incarnation=?",
                                 (row["device"], row["incarnation"]))
            if member is None or member[0]:
                raise JournalError("Origin is not currently trusted")
            result = self._consider(unpack(bytes(row["wire"]))["body"], force=True) if choice == "apply" else ("rejected", "cancelled", [])
            wire = self._finish(row, *result)
            self.db.execute("INSERT INTO journal_reviews VALUES(?,?,?)", (command_id, request_hash, wire))
            self.fault("review_receipt")
        self.fault("review_committed")
        return wire
