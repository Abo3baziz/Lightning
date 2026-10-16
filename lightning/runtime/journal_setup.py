"""Enroll an existing dummy laboratory for cloud and owner-authority tests.

Only a journal-lab.json marked dummy is accepted. No production conversion.
"""
from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from lightning.runtime.instance import InstanceLock
from lightning.runtime.session import read_slot, write_slot
from lightning.security.keys import create_key_file, new_recovery_key
from lightning.sync.journal.authority import AuthorityMemory
from lightning.sync.journal.codec import JournalError, seal
from lightning.sync.journal.membership import Membership
from lightning.sync.journal.owner import OwnerCredential, public_key
from .journal_lab import open_lab


def enroll(root, password, answer):
    root = Path(root)
    marker = root / "journal-lab.json"
    if not marker.is_file() or read_slot(marker).get("dummy") is not True:
        raise JournalError("Only an existing dummy laboratory can enroll")
    if (root / "owner-authority.json").exists() or any((root / f"authority-{name}.db").exists() for name in ("Home", "PC")):
        raise JournalError("Owner enrollment already exists or was interrupted; preserve it for explicit repair")
    devices, secret = open_lab(root, password)
    controls = []
    try:
        home, pc = devices
        members = {device.identity.device_id:dict(key=device.identity.public_key,incarnation=device.store.config["incarnation"]) for device in devices}
        # A running lab may already have paired devices and rotated its key.
        # Preserve that trust rather than silently resetting membership.
        for device in devices:
            trust = Membership(device)
            if device.store.db.scalar("SELECT value FROM journal_local WHERE name='membership'"):
                state = trust.state()
                if any(state["members"].get(identifier) != member for identifier, member in members.items()):
                    raise JournalError("Lab membership differs; preserve it for explicit repair")
        recovery = new_recovery_key()
        key_document = create_key_file(home.c.db.copy_key(), password, recovery, "Your journal recovery answer", answer)
        owner, wrapper = OwnerCredential.create(home.store.config["profile"], password=password, recovery=recovery, answer=answer)
        write_slot(root / "owner-authority.json", wrapper)
        write_slot(root / "keys.json", key_document, replace=True)
        body = dict(type="authority-enrollment", version=1, profile=home.store.config["profile"],
                    generation=home.store.config["generation"], home=home.identity.device_id,
                    home_key=home.identity.public_key, owner_key=owner.public_key)
        wire = seal(body, owner.sign)
        members = {device.identity.device_id:dict(key=device.identity.public_key,incarnation=device.store.config["incarnation"]) for device in devices}
        for device, name in zip(devices, ("Home", "PC")):
            control = AuthorityMemory.enroll(root / f"authority-{name}.db", wire)
            controls.append(control)
            if not device.store.db.scalar("SELECT value FROM journal_local WHERE name='membership'"):
                Membership(device).initialize(members, secret)
            control.bind(device.store)
        provision = dict(profile=body["profile"], generation=body["generation"], home=home.identity.device_id,
                         home_key=public_key(home.identity), owner_key=owner.public_key)
        write_slot(root / "cloud-provision.json", provision)
        write_slot(root / "cloud-members.json", dict(previous=1,version=2,generation=body["generation"],
                   members={device.identity.device_id:public_key(device.identity) for device in devices}))
        return provision, recovery
    finally:
        for control in controls:
            control.close()
        for device in devices:
            device.store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dummy", action="store_true", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    password = getpass.getpass("Existing dummy lab password: ")
    answer = getpass.getpass("Recovery answer (record it privately): ")
    confirm = getpass.getpass("Repeat recovery answer: ")
    if answer != confirm:
        parser.error("Recovery answers do not match")
    with InstanceLock(args.root / "instance.lock"):
        _, recovery = enroll(args.root, password, answer)
    print("Record this dummy lab recovery key privately; it is shown once: " + recovery)
    print("Public deployment inputs: cloud-provision.json and cloud-members.json in the dummy lab directory.")


if __name__ == "__main__":
    main()
