"""Owner proof, durable home fencing, retirement and transport-key revocation."""
import asyncio
import json
import os
from itertools import combinations
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from test_journal_finance import devices, groups
from lightning.runtime.session import AttemptGuard, ProfileError
from lightning.sync.identity import load_or_create
from lightning.sync.journal.authority import AuthorityMemory, AuthorityRegistry, transfer_home_state
from lightning.sync.journal.codec import JournalError, digest, seal, unpack
from lightning.sync.journal.home import JournalHome
from lightning.sync.journal.membership import Membership
from lightning.sync.journal.owner import OwnerCredential, public_key


def memories(devices, tmp_path):
    home, pc = devices
    owner = OwnerCredential(ec.generate_private_key(ec.SECP256R1()))
    config = home.store.config
    wire = seal(dict(type="authority-enrollment", version=1, profile=config["profile"], generation=config["generation"],
                     home=config["device"], home_key=config["home_key"], owner_key=owner.public_key), owner.sign)
    result = [AuthorityMemory.enroll(tmp_path / f"control-{i}.db", wire) for i in range(2)]
    for device, memory in zip(devices, result):
        memory.bind(device.store)
    return owner, result


def change(home, pc, owner, *, mode="move"):
    return seal(dict(profile=home.store.config["profile"], previous=home.store.config["generation"],
                     generation=str(uuid4()), home=pc.identity.device_id, home_key=public_key(pc.identity),
                     owner_key=owner.public_key, version=2, mode=mode, nonce=os.urandom(32).hex(), cutoff=pc.store.cursor()), owner.sign)


def test_each_two_secret_pair_opens_independent_owner_key_but_one_secret_and_data_key_do_not(tmp_path, monkeypatch):
    import lightning.sync.journal.owner as module
    monkeypatch.setattr(module, "RECOVERY_MEMORY_KIB", 32768)
    monkeypatch.setattr(module, "RECOVERY_ITERATIONS", 2)
    values = dict(password="profile password", recovery="1234-5678-9012", answer="First school")
    original, document = OwnerCredential.create(str(uuid4()), **values)
    guard = AttemptGuard(tmp_path / "attempts.json")
    for pair in combinations(values, 2):
        opened = OwnerCredential.unlock(document, {name: values[name] for name in pair}, guard=guard)
        assert opened.public_key == original.public_key
    with pytest.raises(JournalError):
        OwnerCredential.unlock(document, dict(password=values["password"]), guard=guard)
    wrong = dict(password=values["password"], answer="wrong answer")
    for _ in range(4):
        with pytest.raises(JournalError):
            OwnerCredential.unlock(document, wrong, guard=guard)
    with pytest.raises(ProfileError, match="Too many"):
        OwnerCredential.unlock(document, dict(password=values["password"], answer=values["answer"]), guard=guard)
    assert "private" not in json.dumps(document)
    changed = dict(document, profile=str(uuid4()))
    with pytest.raises(JournalError):
        OwnerCredential.unlock(changed, dict(password=values["password"], recovery=values["recovery"]), guard=AttemptGuard(tmp_path / "other.json"))


def test_frozen_home_cannot_confirm_or_review_and_missing_control_never_resets(devices, tmp_path):
    home, pc = devices
    owner, controls = memories(devices, tmp_path)
    try:
        home.save(groups(home))
        controls[0].freeze(home.store)
        with pytest.raises(JournalError, match="frozen|retired"):
            home.home.process()
        home.store.authority = None
        with pytest.raises(JournalError, match="required"):
            home.home.process()
        with pytest.raises(JournalError, match="missing"):
            AuthorityMemory(tmp_path / "missing.db", profile=home.store.config["profile"])
    finally:
        for control in controls:
            control.close()


def test_cooperative_move_retires_old_home_before_activation_and_keeps_original_pending_ids(devices, tmp_path):
    home, pc = devices
    owner, controls = memories(devices, tmp_path)
    try:
        home.save(groups(home))
        pc.sync_with(home.home)
        queued = pc.save(groups(pc, "-8"))
        controls[0].freeze(home.store)
        transfer_home_state(home.store, pc.store)
        wire = change(home, pc, owner)
        prepared = controls[1].prepare(pc.store, wire, pc.identity.sign)
        with pytest.raises(JournalError):
            controls[1].activate_move(pc.store, wire, prepared, prepared, old_home_key=home.identity.public_key)
        assert controls[1].state()["phase"] == "prepared"
        retired = controls[0].retire(home.store, wire, prepared, home.identity.sign)
        assert controls[0].state()["phase"] == "retired"
        controls[1].activate_move(pc.store, wire, prepared, retired, old_home_key=home.identity.public_key)
        pc.home = JournalHome(pc.store, pc.identity.sign)
        pc.flush_home()
        assert not pc.store.pending()
        assert pc.store.cursor()["revision"] == 2
        assert pc.store.db.scalar("SELECT wire FROM journal_outbox WHERE seq=1") == queued
        with pytest.raises(JournalError):
            home.home.process()
        with pytest.raises(JournalError, match="Stale|competing"):
            controls[1].observe(wire, local_device=pc.identity.device_id)
    finally:
        for control in controls:
            control.close()


def test_recovery_requires_live_registry_publication_and_preserves_old_branch(devices, tmp_path):
    home, pc = devices
    owner, controls = memories(devices, tmp_path)
    wire = change(home, pc, owner, mode="recover")
    class Unavailable:
        async def publish(self, request):
            raise OSError("offline")
    class Registry:
        async def publish(self, request):
            assert request == wire
    try:
        with pytest.raises(OSError):
            asyncio.run(controls[1].recover(pc.store, wire, Unavailable()))
        assert controls[1].state()["generation"] == home.store.config["generation"]
        asyncio.run(controls[1].recover(pc.store, wire, Registry()))
        assert controls[1].can_confirm(pc.store)
        # An offline old home can still make a branch until it learns retirement.
        home.save(groups(home, "-12"))
        original = bytes(home.store.db.scalar("SELECT wire FROM journal_outbox WHERE seq=1"))
        controls[0].observe(wire, local_device=home.identity.device_id)
        with pytest.raises(JournalError):
            home.home.process()
        pc.home = JournalHome(pc.store, pc.identity.sign)
        # Production must reapprove surviving origins in new registry membership.
        pc.home.approve_origin(home.identity.device_id, home.store.config["incarnation"], home.identity.public_key)
        pc.home.receive(original)
        pc.home.process()
        assert pc.store.cursor()["revision"] == 1
        assert next(item for item in pc.balances() if item["name"] == "Bank")["balance"] == 988
    finally:
        for control in controls:
            control.close()


def test_registry_checks_the_winning_certificate_instead_of_trusting_a_reply(devices, tmp_path):
    home, pc = devices
    owner, controls = memories(devices, tmp_path)
    wire = change(home, pc, owner, mode="recover")
    class ForgedReply:
        async def call(self, route, data=None):
            return dict(activated=True) if route.endswith("transition") else dict(generation=str(uuid4()),version=2)
    try:
        with pytest.raises(JournalError, match="another successor"):
            asyncio.run(AuthorityRegistry(ForgedReply()).publish(wire))
        assert not controls[1].can_confirm(pc.store)
    finally:
        for control in controls:
            control.close()


def test_revoked_device_cannot_derive_rotated_transport_secret_from_old_key_or_data_key(devices, tmp_path):
    home, pc = devices
    members = {device.identity.device_id: dict(key=device.identity.public_key,incarnation=device.store.config["incarnation"]) for device in devices}
    secret = os.urandom(32)
    hm, pm = Membership(home), Membership(pc)
    hm.initialize(members, secret)
    pm.initialize(members, secret)
    newcomer = load_or_create(tmp_path / "new-device", "New device")
    expanded = members | {newcomer.device_id: dict(key=newcomer.public_key,incarnation=str(uuid4()))}
    wire = hm.rotate(expanded)
    pm.accept(wire)
    assert home.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'") == pc.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'")
    assert bytes.fromhex(pc.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'")) != secret
    revoked = hm.rotate({home.identity.device_id:members[home.identity.device_id]})
    assert pc.identity.device_id not in unpack(revoked)["body"]["wrapped"]
    with pytest.raises(JournalError, match="no longer"):
        pm.accept(revoked)
    with pytest.raises(JournalError, match="retired"):
        hm.rotate(members)
    assert bytes.fromhex(home.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'")) != home.c.db.copy_key()


def test_pairing_requires_code_password_both_keys_and_explicit_matching_digits(devices):
    from lightning.security.keys import create_key_file
    from lightning.sync.journal.pairing import PairingDesk, request_pairing
    home, pc = devices
    hm, pm = Membership(home), Membership(pc)
    home_only = {home.identity.device_id:dict(key=home.identity.public_key,incarnation=home.store.config["incarnation"])}
    hm.initialize(home_only, os.urandom(32))
    password = "Dummy pairing password"
    key_file = create_key_file(home.c.db.copy_key(), password, "1234-5678-9012", "First school?", "Cairo")
    desk = PairingDesk(home, hm)
    offer, code = desk.begin(key_file, password)
    bad, _ = request_pairing(offer, code, "wrong password", pc.identity, pc.store.config["incarnation"], home_key=home.identity.public_key)
    with pytest.raises(JournalError, match="wrong"):
        desk.accept(bad)
    request, digits = request_pairing(offer, code, password, pc.identity, pc.store.config["incarnation"], home_key=home.identity.public_key)
    assert desk.accept(request) == digits
    assert pc.identity.device_id not in hm.state()["members"]
    with pytest.raises(JournalError, match="same six"):
        desk.confirm("000000" if digits != "000000" else "000001")
    update = desk.confirm(digits)
    pm.accept(update, initial=True)
    assert hm.state() == pm.state()
    assert home.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'") == pc.c.db.scalar("SELECT value FROM journal_local WHERE name='transport'")
    with pytest.raises(JournalError):
        desk.accept(request)
