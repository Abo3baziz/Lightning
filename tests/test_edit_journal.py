"""J1 laboratory: encrypted saves, ordering, exact replay, review and failures.

These tests use dummy record adapters. They prove neither production financial
invariants nor Android availability nor physical power-loss durability.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass
from uuid import uuid4

import pytest

from lightning.sync.identity import load_or_create
from lightning.sync.journal.codec import (JournalError, MAX_MESSAGE, ZERO_HASH, canonical,
                                          digest, origin_id, seal, unpack)
from lightning.sync.journal.home import JournalHome
from lightning.sync.journal.store import JournalStore


def uid():
    return str(uuid4())


@dataclass
class Device:
    store: JournalStore
    identity: object
    path: object
    key: bytes

    def save(self, record=None, groups=None, *, kind="dummy.add", bases=None, dependencies=(), **kwargs):
        groups = {"amount": "10.00", "category": "coffee"} if groups is None else groups
        return self.store.save(kind=kind, record=record or uid(), groups=groups,
                               bases=dict.fromkeys(groups) if bases is None else bases,
                               dependencies=dependencies, signer=self.identity.sign, **kwargs)

    def restart(self):
        self.store.close()
        self.store = JournalStore.open(self.path, key=self.key)
        return self.store


@pytest.fixture
def lab(tmp_path):
    pytest.importorskip("sqlcipher3")
    devices = []
    profile, generation = uid(), uid()
    home_identity = load_or_create(tmp_path / "identity-home", "Home")

    def make(name, role="replica"):
        identity = home_identity if role == "home" else load_or_create(tmp_path / f"identity-{name}", name)
        path = tmp_path / f"{name}.db"
        key = os.urandom(32)
        store = JournalStore.create(path, key=key, profile=profile, generation=generation,
                                    device=identity.device_id, incarnation=uid(),
                                    home_key=home_identity.public_key, origin_key=identity.public_key, role=role)
        device = Device(store, identity, path, key)
        devices.append(device)
        return device

    home_device = make("home", "home")
    home = JournalHome(home_device.store, home_identity.sign)
    first, second = make("PC"), make("Phone")
    for device in devices:
        home.approve_origin(device.identity.device_id, device.store.config["incarnation"], device.identity.public_key)
    yield home, home_device, first, second
    for device in devices:
        device.store.close()


def body(wire):
    return unpack(wire)["body"]


def identifier(wire):
    return origin_id(body(wire)["origin"])


def confirm(home, wire):
    home.receive(wire)
    return home.process()


def replay(device, commits):
    for wire in commits:
        device.store.apply(wire)


def test_offline_save_is_encrypted_durable_and_not_in_confirmed_figures(lab):
    home, hd, pc, phone = lab
    fingerprint = pc.store.fingerprint()
    saved = pc.save(groups={"note": "private dummy text"})
    assert pc.store.pending() == [saved]
    assert pc.store.fingerprint() == fingerprint
    assert pc.store.record(body(saved)["record"]) is None
    pc.restart()
    assert pc.store.pending() == [saved]
    assert b"private dummy text" not in pc.path.read_bytes()
    commits = confirm(home, saved)
    replay(pc, commits)
    replay(phone, commits)
    assert not pc.store.pending()
    assert pc.store.decisions()[0]["displayed"] == 0
    pc.store.mark_displayed(identifier(saved))
    pc.restart()
    assert pc.store.decisions()[0]["displayed"] == 1
    assert pc.store.fingerprint() == phone.store.fingerprint() == hd.store.fingerprint()


def test_home_uses_the_same_outbox_save_path(lab):
    home, hd, pc, _ = lab
    saved = hd.save()
    assert hd.store.pending() == [saved]
    commits = confirm(home, saved)
    assert not hd.store.pending()
    replay(pc, commits)
    assert hd.store.fingerprint() == pc.store.fingerprint()


def test_retry_and_altered_identity_after_restarts(lab):
    home, hd, pc, _ = lab
    saved = pc.save()
    commit = confirm(home, saved)[0]
    home = JournalHome(hd.restart(), hd.identity.sign)
    assert home.receive(saved) == "accepted"
    assert home.decision(identifier(saved)) == commit
    assert home.process() == []
    changed = body(saved)
    changed["groups"]["amount"] = "999.00"
    with pytest.raises(JournalError, match="reused"):
        home.receive(seal(changed, pc.identity.sign))
    assert pc.store.apply(commit)
    assert not pc.store.apply(commit)
    assert hd.store.cursor()["revision"] == 1


def test_add_then_edit_then_delete_before_upload_and_out_of_order_delivery(lab):
    home, hd, pc, phone = lab
    add = pc.save()
    edit = pc.save(body(add)["record"], {"amount": "12.00"}, kind="dummy.edit",
                   dependencies=[body(add)["origin"]])
    delete = pc.save(body(add)["record"], {"amount": None, "category": None}, kind="dummy.delete",
                     dependencies=[body(add)["origin"], body(edit)["origin"]],
                     bases={"amount": digest(dict(proposal=digest(body(edit)), group="amount")),
                            "category": digest(dict(proposal=digest(body(add)), group="category"))})
    home.receive(delete)
    home.receive(edit)
    assert home.process() == []
    commits = confirm(home, add)
    assert len(commits) == 3
    replay(pc, commits)
    replay(phone, commits)
    assert hd.store.record(body(add)["record"]) == dict(record=body(add)["record"], groups={}, tokens={}, deleted=True)
    assert not pc.store.pending()
    assert hd.store.fingerprint() == pc.store.fingerprint() == phone.store.fingerprint()


def test_rejected_parent_rejects_children_and_advances_origin(lab):
    home, hd, pc, _ = lab
    missing = pc.save(kind="dummy.edit")
    child = pc.save(body(missing)["record"], kind="dummy.edit", dependencies=[body(missing)["origin"]])
    home.receive(child)
    commits = confirm(home, missing)
    assert [body(w)["reason"] for w in commits] == ["missing-record", "dependency-rejected"]
    replay(pc, commits)
    assert not pc.store.pending()
    assert hd.store.cursor()["revision"] == 2


def shared_record(home, devices, creator):
    add = creator.save()
    commits = confirm(home, add)
    for device in devices:
        replay(device, commits)
    record = body(add)["record"]
    return record, creator.store.record(record)["tokens"]


def test_independent_groups_merge_and_same_group_waits_without_blocking_other_origins(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    amount = pc.save(record, {"amount": "12.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    category = phone.save(record, {"category": "food"}, kind="dummy.edit", bases={"category": tokens["category"]})
    commits = confirm(home, amount) + confirm(home, category)
    assert hd.store.record(record)["groups"] == {"amount": "12.00", "category": "food"}
    replay(pc, commits)
    replay(phone, commits)
    conflict = phone.save(record, {"amount": "15.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    home.receive(conflict)
    blocked = phone.save()
    home.receive(blocked)
    assert home.process() == []
    assert home.status(identifier(conflict))["status"] == "review"
    other = pc.save()
    assert len(confirm(home, other)) == 1
    state = home.review_state(identifier(conflict))
    command = dict(command_id=uid(), proposal_id=identifier(conflict), token=state["token"], choice="apply")
    commit = home.review(**command)
    assert body(commit)["outcome"] == "accepted"
    assert home.review(**command) == commit
    with pytest.raises(JournalError, match="reused"):
        home.review(**(command | {"choice": "reject"}))
    assert len(home.process()) == 1
    assert home.status(identifier(blocked))["status"] == "accepted"
    assert hd.store.record(record)["groups"]["amount"] == "15.00"


def test_stale_review_cannot_overwrite_newer_changes(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    first = pc.save(record, {"amount": "11.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    confirm(home, first)
    conflict = phone.save(record, {"amount": "15.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    confirm(home, conflict)
    state = home.review_state(identifier(conflict))
    latest = hd.store.record(record)["tokens"]["amount"]
    confirm(home, pc.save(record, {"amount": "20.00"}, kind="dummy.edit", bases={"amount": latest}))
    with pytest.raises(JournalError, match="refresh"):
        home.review(command_id=uid(), proposal_id=identifier(conflict), token=state["token"], choice="apply")
    assert hd.store.record(record)["groups"]["amount"] == "20.00"
    refreshed = home.review_state(identifier(conflict))
    refusal = home.review(command_id=uid(), proposal_id=identifier(conflict), token=refreshed["token"], choice="reject")
    assert body(refusal)["reason"] == "cancelled"


def test_changed_and_changed_back_still_conflicts_and_delete_needs_all_groups(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    for value in ("11.00", "10.00"):
        latest = hd.store.record(record)["tokens"]["amount"]
        confirm(home, pc.save(record, {"amount": value}, kind="dummy.edit", bases={"amount": latest}))
    stale = phone.save(record, {"amount": "12.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    confirm(home, stale)
    assert home.status(identifier(stale))["status"] == "review"
    delete = pc.save(record, {}, kind="dummy.delete")
    confirm(home, delete)
    assert home.status(identifier(delete))["status"] == "review"
    assert not hd.store.record(record)["deleted"]


def test_tombstone_prevents_recreation_and_stale_edits(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    delete = pc.save(record, dict.fromkeys(tokens), bases=tokens, kind="dummy.delete")
    confirm(home, delete)
    stale = phone.save(record, {"amount": "12.00"}, bases={"amount": tokens["amount"]}, kind="dummy.edit")
    recreate = pc.save(record)
    for wire in (stale, recreate):
        assert body(confirm(home, wire)[0])["reason"] == "deleted"
    assert hd.store.record(record)["deleted"]


def test_wrong_generation_membership_signature_and_gap_change_no_state(lab):
    home, hd, pc, phone = lab
    saved = pc.save()
    value = body(saved)
    bad_messages = [seal(value, phone.identity.sign),
                    seal(value | {"generation": uid()}, pc.identity.sign),
                    seal(value | {"profile": uid()}, pc.identity.sign),
                    seal(value | {"origin": value["origin"] | {"seq": 300}}, pc.identity.sign),
                    seal(value | {"kind": "production.transfer"}, pc.identity.sign),
                    seal(value | {"kind": []}, pc.identity.sign),
                    seal(value | {"unexpected": True}, pc.identity.sign)]
    for wire in bad_messages:
        with pytest.raises(JournalError):
            home.receive(wire)
    assert hd.store.db.scalar("SELECT COUNT(*) FROM journal_inbox") == 0
    home.revoke_origin(pc.identity.device_id, pc.store.config["incarnation"])
    with pytest.raises(JournalError, match="trusted"):
        home.receive(saved)
    with pytest.raises(JournalError, match="revived"):
        home.approve_origin(pc.identity.device_id, pc.store.config["incarnation"], pc.identity.public_key)


def test_wrong_local_signer_does_not_consume_a_sequence(lab):
    _, _, pc, phone = lab
    with pytest.raises(JournalError, match="signature"):
        pc.store.save(kind="dummy.add", record=uid(), groups={"note": "dummy"},
                      bases={"note": None}, signer=phone.identity.sign)
    assert not pc.store.pending()
    assert body(pc.save())["origin"]["seq"] == 1


def test_divergent_checkpoint_and_cross_origin_dependency_are_refused(lab):
    home, hd, pc, phone = lab
    confirm(home, pc.save())
    with pytest.raises(JournalError, match="checkpoint"):
        hd.store.commits_after({"revision": 1, "hash": ZERO_HASH})
    with pytest.raises(JournalError, match="this origin"):
        phone.save(dependencies=[body(pc.store.pending()[0])["origin"]])


def test_oversized_result_is_rejected_atomically_without_losing_following_edits(lab):
    home, hd, pc, _ = lab
    record = uid()
    add = pc.save(record, {"one": "a" * 16000, "two": "b" * 16000})
    confirm(home, add)
    tokens = hd.store.record(record)["tokens"]
    edit = pc.save(record, {"three": "c" * 16000, "four": "d" * 16000}, kind="dummy.edit")
    decision = confirm(home, edit)[0]
    assert body(decision)["reason"] == "effect-too-large"
    assert hd.store.record(record)["tokens"] == tokens
    assert body(confirm(home, pc.save())[0])["outcome"] == "accepted"


def test_revocation_stops_staged_work_and_review_acceptance(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    confirm(home, pc.save(record, {"amount": "12.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]}))
    conflict = phone.save(record, {"amount": "15.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    confirm(home, conflict)
    state = home.review_state(identifier(conflict))
    staged = phone.save()
    home.receive(staged)
    home.revoke_origin(phone.identity.device_id, phone.store.config["incarnation"])
    assert home.process() == []
    with pytest.raises(JournalError, match="trusted"):
        home.review(command_id=uid(), proposal_id=identifier(conflict), token=state["token"], choice="apply")
    assert home.status(identifier(staged))["status"] == "staged"


@pytest.mark.parametrize("wire", [b'{"body":{},"body":{},"signature":"abcd"}', b"[NaN]", b"[1.5]", b"[" * 100,
                                   b"x" * (MAX_MESSAGE + 1), b'{"body":{}, "signature":"aaaaaaaaaaaaaaaa"}'])
def test_codec_refuses_ambiguous_or_unbounded_messages(wire):
    with pytest.raises(JournalError):
        unpack(wire)


def test_replica_refuses_missing_predecessor_unknown_schema_forgery_and_bad_fingerprint(lab):
    home, hd, pc, phone = lab
    commits = confirm(home, pc.save()) + confirm(home, pc.save())
    initial = phone.store.cursor()
    invalid = [commits[1], seal(body(commits[0]), pc.identity.sign),
               seal(body(commits[0]) | {"version": 3}, hd.identity.sign),
               seal(body(commits[0]) | {"outcome": []}, hd.identity.sign),
               seal(body(commits[0]) | {"fingerprint": ZERO_HASH}, hd.identity.sign),
               seal(body(commits[0]) | {"effects": [{"sql": "DELETE FROM ledger"}]}, hd.identity.sign)]
    for wire in invalid:
        with pytest.raises(JournalError):
            phone.store.apply(wire)
        assert phone.store.cursor() == initial
        assert phone.store.db.scalar("SELECT COUNT(*) FROM journal_records") == 0
    replay(phone, commits)
    assert phone.store.fingerprint() == hd.store.fingerprint()
    divergent = body(commits[0]) | {"reason": "cancelled", "outcome": "rejected", "effects": []}
    with pytest.raises(JournalError, match="Divergent"):
        phone.store.apply(seal(divergent, hd.identity.sign))


class InjectedCrash(BaseException):
    pass


def crash_at(expected):
    def fault(phase):
        if phase == expected:
            raise InjectedCrash(phase)
    return fault


@pytest.mark.parametrize("phase", ["outbox_inserted", "counter_advanced", "saved"])
def test_save_failure_boundaries_are_atomic(lab, phase):
    _, _, pc, _ = lab
    with pytest.raises(InjectedCrash):
        pc.save(fault=crash_at(phase))
    pc.restart()
    pending = pc.store.pending()
    assert len(pending) == (1 if phase == "saved" else 0)
    following = pc.save()
    assert body(following)["origin"]["seq"] == len(pending) + 1


@pytest.mark.parametrize("phase", ["inbox_inserted", "inbox_committed", "home_effects", "home_receipt", "decision_committed"])
def test_home_failure_boundaries_keep_receipts_and_records_together(lab, phase):
    home, hd, pc, _ = lab
    saved = pc.save()
    home.fault = crash_at(phase)
    with pytest.raises(InjectedCrash):
        home.receive(saved)
        home.process()
    home = JournalHome(hd.restart(), hd.identity.sign)
    home.receive(saved)
    home.process()
    assert hd.store.cursor()["revision"] == 1
    assert hd.store.db.scalar("SELECT COUNT(*) FROM journal_records") == 1
    assert home.status(identifier(saved))["status"] == "accepted"


@pytest.mark.parametrize("phase", ["replica_effects", "replica_cursor", "replica_committed"])
def test_replica_failure_boundaries_keep_effects_and_cursor_together(lab, phase):
    home, hd, pc, _ = lab
    saved = pc.save()
    commit = confirm(home, saved)[0]
    with pytest.raises(InjectedCrash):
        pc.store.apply(commit, fault=crash_at(phase))
    pc.restart()
    assert pc.store.cursor()["revision"] == (1 if phase == "replica_committed" else 0)
    pc.store.apply(commit)
    assert not pc.store.pending()
    assert pc.store.fingerprint() == hd.store.fingerprint()


def test_actual_sqlite_full_does_not_report_a_save_or_consume_sequence(lab):
    _, _, pc, _ = lab
    count = pc.store.db.scalar("PRAGMA page_count")
    pc.store.db.conn.execute(f"PRAGMA max_page_count={count}")
    with pytest.raises(pc.store.db.OperationalError, match="full"):
        pc.save(groups={"note": "x" * 16000})
    pc.restart()
    assert pc.store.pending() == []
    assert body(pc.save())["origin"]["seq"] == 1


def test_missing_damaged_or_unencrypted_store_never_reinitializes(lab, tmp_path):
    _, _, pc, _ = lab
    with pytest.raises(JournalError, match="encryption"):
        JournalStore.open(pc.path, key=None)
    with pytest.raises(JournalError, match="Missing"):
        JournalStore.open(tmp_path / "lost.db", key=pc.key)
    assert not (tmp_path / "lost.db").exists()
    with pytest.raises(JournalError, match="existing"):
        JournalStore.create(pc.path, key=pc.key, **{k: v for k, v in pc.store.config.items() if k != "version"})
    with pc.store.db.transaction():
        pc.store.db.execute("UPDATE journal_meta SET next_seq=0")
    with pytest.raises(JournalError, match="repair"):
        pc.restart()


def test_initialization_refuses_dangling_symlinks_without_creating_the_target(lab, tmp_path):
    _, _, pc, _ = lab
    target, link = tmp_path / "uncreated.db", tmp_path / "link.db"
    link.symlink_to(target)
    with pytest.raises(JournalError, match="existing"):
        JournalStore.create(link, key=pc.key, **{k: v for k, v in pc.store.config.items() if k != "version"})
    assert not target.exists()


@pytest.mark.parametrize("damage", ["UPDATE journal_meta SET next_seq=4", "DELETE FROM journal_outbox WHERE seq=1"])
def test_uncertain_counter_or_missing_sequence_requires_repair(lab, damage):
    _, _, pc, _ = lab
    pc.save()
    pc.save()
    with pc.store.db.transaction():
        pc.store.db.execute(damage)
    with pytest.raises(JournalError, match="repair"):
        pc.restart()


@pytest.mark.parametrize("seed", range(5))
def test_seeded_loss_duplication_reordering_and_eventual_catchup(lab, seed):
    home, hd, pc, phone = lab
    rng = random.Random(seed)
    queued = []
    for device in (pc, phone, hd):
        for _ in range(12):
            add = device.save()
            edit = device.save(body(add)["record"], {"amount": str(rng.randrange(100))}, kind="dummy.edit",
                               dependencies=[body(add)["origin"]])
            queued.extend([add, edit])
    deliveries = queued + rng.sample(queued, 24)
    rng.shuffle(deliveries)
    source = {identifier(wire): body(wire) for wire in queued}
    expected, decided = {}, set()

    def receive_and_check(wire):
        home.receive(wire)
        for commit in home.process():
            decision = body(commit)
            assert decision["outcome"] == "accepted"
            assert decision["proposal_id"] not in decided
            decided.add(decision["proposal_id"])
            action = source[decision["proposal_id"]]
            if action["kind"] == "dummy.add":
                assert action["record"] not in expected
                expected[action["record"]] = dict(action["groups"])
            else:
                assert action["record"] in expected
                expected[action["record"]].update(action["groups"])
        # Independent domain model after every delivery, including duplicate and
        # out-of-order deliveries, rather than just agreement among replicas.
        actual = {row["record_id"]: json.loads(row["groups_json"])
                  for row in hd.store.db.all("SELECT record_id,groups_json FROM journal_records WHERE deleted=0")}
        assert actual == expected
        assert hd.store.cursor()["revision"] == len(decided)

    for wire in deliveries[:50]:  # interrupted communication, followed by complete retry
        receive_and_check(wire)
    rng.shuffle(queued)
    for wire in queued:
        receive_and_check(wire)
    assert hd.store.cursor()["revision"] == 72
    for device in (pc, phone):
        while device.store.cursor() != hd.store.cursor():
            batch = hd.store.commits_after(device.store.cursor(), limit=7)
            for commit in batch:
                device.store.apply(commit)
                assert not device.store.apply(commit)
        assert device.store.pending() == []
        assert device.store.fingerprint() == hd.store.fingerprint()


@pytest.mark.parametrize("phase", ["outbox_inserted", "counter_advanced", "saved"])
def test_process_exit_during_encrypted_save(lab, phase):
    _, _, pc, _ = lab
    pc.store.close()
    script = '''
import os, sys
from lightning.sync.identity import load_or_create
from lightning.sync.journal.store import JournalStore
store = JournalStore.open(sys.argv[1], key=bytes.fromhex(sys.argv[2]))
identity = load_or_create(sys.argv[3], "PC")
def fault(point):
    if point == sys.argv[4]:
        os._exit(81)
store.save(kind="dummy.add", record=sys.argv[5], groups={"note":"crash test"},
           bases={"note":None}, signer=identity.sign, fault=fault)
'''
    result = subprocess.run([sys.executable, "-c", script, str(pc.path), pc.key.hex(),
                             str(pc.path.parent / "identity-PC"), phase, uid()], capture_output=True, timeout=30)
    assert result.returncode == 81, result.stderr.decode()
    pc.restart()
    assert len(pc.store.pending()) == (1 if phase == "saved" else 0)
    assert body(pc.save())["origin"]["seq"] == (2 if phase == "saved" else 1)


@pytest.mark.parametrize("phase", ["home_effects", "home_receipt", "decision_committed"])
def test_process_exit_during_home_confirmation(lab, phase):
    home, hd, pc, _ = lab
    saved = pc.save()
    home.receive(saved)
    hd.store.close()
    script = '''
import os, sys
from lightning.sync.identity import load_or_create
from lightning.sync.journal.store import JournalStore
from lightning.sync.journal.home import JournalHome
store = JournalStore.open(sys.argv[1], key=bytes.fromhex(sys.argv[2]))
identity = load_or_create(sys.argv[3], "Home")
def fault(point):
    if point == sys.argv[4]:
        os._exit(82)
JournalHome(store, identity.sign, fault=fault).process()
'''
    result = subprocess.run([sys.executable, "-c", script, str(hd.path), hd.key.hex(),
                             str(hd.path.parent / "identity-home"), phase], capture_output=True, timeout=30)
    assert result.returncode == 82, result.stderr.decode()
    home = JournalHome(hd.restart(), hd.identity.sign)
    assert hd.store.cursor()["revision"] == (1 if phase == "decision_committed" else 0)
    home.receive(saved)
    home.process()
    assert hd.store.cursor()["revision"] == 1
    assert home.status(identifier(saved))["status"] == "accepted"


@pytest.mark.parametrize("phase", ["replica_effects", "replica_cursor", "replica_committed"])
def test_process_exit_during_replica_replay(lab, phase, tmp_path):
    home, hd, pc, _ = lab
    commit = confirm(home, pc.save())[0]
    stream = tmp_path / "signed-commit.json"
    stream.write_bytes(commit)  # dummy data only
    pc.store.close()
    script = '''
import os, sys
from pathlib import Path
from lightning.sync.journal.store import JournalStore
store = JournalStore.open(sys.argv[1], key=bytes.fromhex(sys.argv[2]))
def fault(point):
    if point == sys.argv[4]:
        os._exit(83)
store.apply(Path(sys.argv[3]).read_bytes(), fault=fault)
'''
    result = subprocess.run([sys.executable, "-c", script, str(pc.path), pc.key.hex(),
                             str(stream), phase], capture_output=True, timeout=30)
    assert result.returncode == 83, result.stderr.decode()
    pc.restart()
    assert pc.store.cursor()["revision"] == (1 if phase == "replica_committed" else 0)
    pc.store.apply(commit)
    assert not pc.store.pending()
    assert pc.store.fingerprint() == hd.store.fingerprint()


def test_review_crash_does_not_leave_a_decision_without_its_control_receipt(lab):
    home, hd, pc, phone = lab
    record, tokens = shared_record(home, [pc, phone], pc)
    confirm(home, pc.save(record, {"amount": "12.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]}))
    conflict = phone.save(record, {"amount": "15.00"}, kind="dummy.edit", bases={"amount": tokens["amount"]})
    confirm(home, conflict)
    state = home.review_state(identifier(conflict))
    command = dict(command_id=uid(), proposal_id=identifier(conflict), token=state["token"], choice="apply")
    home.fault = crash_at("review_receipt")
    with pytest.raises(InjectedCrash):
        home.review(**command)
    home = JournalHome(hd.restart(), hd.identity.sign)
    assert hd.store.record(record)["groups"]["amount"] == "12.00"
    decision = home.review(**command)
    assert home.review(**command) == decision
    assert hd.store.cursor()["revision"] == 3


def test_simulation_command_produces_a_converged_metrics_artifact():
    from lightning.sync.journal.__main__ import simulate
    result = simulate(seed=16, additions=4)
    assert result["converged"] and not result["production_ready"]
    assert result["confirmed_revision"] == result["proposals"] == 24
    assert result["pending"] == [0, 0, 0]
    assert result["proposal_deliveries"] > result["proposals"]
