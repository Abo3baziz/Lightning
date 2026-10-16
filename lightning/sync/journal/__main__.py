"""Run an isolated, encrypted three-device journal simulation; no live data."""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from lightning.sync.identity import load_or_create

from .codec import unpack
from .home import JournalHome
from .store import JournalStore


def simulate(*, seed=1, additions=40):
    if type(additions) is not int or not 1 <= additions <= 5000:
        raise ValueError("Use between 1 and 5000 dummy additions per origin")
    rng = random.Random(seed)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="lightning-journal-lab-") as folder:
        root = Path(folder)
        identities = [load_or_create(root / f"identity-{n}", f"Lab device {n}") for n in range(3)]
        profile, generation = str(uuid4()), str(uuid4())
        stores = []
        try:
            for n, identity in enumerate(identities):
                stores.append(JournalStore.create(root / f"device-{n}.db", key=os.urandom(32),
                    profile=profile, generation=generation, device=identity.device_id,
                    incarnation=str(uuid4()), home_key=identities[0].public_key,
                    origin_key=identity.public_key, role="home" if n == 0 else "replica"))
            home = JournalHome(stores[0], identities[0].sign)
            for store, identity in zip(stores, identities):
                home.approve_origin(identity.device_id, store.config["incarnation"], identity.public_key)
            proposals = []
            # Each device saves while disconnected, then edits its own pending records.
            for store, identity in zip(stores, identities):
                for index in range(additions):
                    record = str(uuid4())
                    add = store.save(kind="dummy.add", record=record, groups={"note": f"Dummy {index}"},
                                     bases={"note": None}, signer=identity.sign)
                    parent = unpack(add)["body"]["origin"]
                    edit = store.save(kind="dummy.edit", record=record, groups={"note": f"Edited {index}"},
                                      bases={"note": None}, dependencies=[parent], signer=identity.sign)
                    proposals.extend((add, edit))
            # Bounded delivery windows model repeated losses and reconnects without
            # exceeding the initial protocol's 256-sequence staging bound.
            sent_bytes = 0
            sent_count = 0
            for start in range(0, len(proposals), 100):
                window = proposals[start:start + 100]
                noisy = window + rng.sample(window, max(1, len(window) // 3))
                rng.shuffle(noisy)
                for wire in noisy[:len(noisy) // 2]:
                    home.receive(wire)
                    home.process()
                    sent_bytes += len(wire)
                    sent_count += 1
                rng.shuffle(window)
                for wire in window:
                    home.receive(wire)
                    home.process()
                    sent_bytes += len(wire)
                    sent_count += 1
            confirmed_bytes = 0
            for replica in stores[1:]:
                while replica.cursor() != stores[0].cursor():
                    batch = stores[0].commits_after(replica.cursor())
                    if not batch:
                        raise RuntimeError("Simulation stalled before convergence")
                    for wire in batch:
                        replica.apply(wire)
                        confirmed_bytes += len(wire)
            fingerprints = [store.fingerprint() for store in stores]
            pending = [len(store.pending()) for store in stores]
            if len(set(fingerprints)) != 1 or any(pending):
                raise RuntimeError("Journal invariants failed")
            return dict(protocol="v2 laboratory", production_ready=False, seed=seed, devices=3,
                        domain="dummy records only", additions=additions * 3,
                        proposals=len(proposals), proposal_deliveries=sent_count,
                        proposal_bytes_with_retries=sent_bytes, confirmed_bytes_to_two_replicas=confirmed_bytes,
                        confirmed_revision=stores[0].cursor()["revision"], pending=pending,
                        converged=True, fingerprint=fingerprints[0], snapshots=0,
                        elapsed_seconds=round(time.monotonic() - started, 3))
        finally:
            for store in stores:
                store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--additions", type=int, default=40, help="Dummy additions per origin; each is followed by an edit")
    parser.add_argument("--report", type=Path, help="Write non-financial simulation metrics as JSON")
    args = parser.parse_args()
    result = simulate(seed=args.seed, additions=args.additions)
    output = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
