"""Measure real cash-service delta bytes against the encrypted whole-file baseline.

Uses a disposable dummy lab. This measures encoded application bytes, not TLS/IP
overhead, phone wake-up latency, internet costs or physical power-loss durability.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lightning.core.dates import today
from lightning.runtime.journal_lab import open_lab
from lightning.sync.journal.local import LocalChannel


def measure(edits=30):
    if not 1 <= edits <= 100:
        raise ValueError("Measure between 1 and 100 small edits")
    with tempfile.TemporaryDirectory(prefix="lightning-journal-measure-") as folder:
        devices, secret = open_lab(Path(folder), "Disposable measurement password")
        home, pc = devices
        try:
            baseline = Path(home.store.db.path).stat().st_size
            server = LocalChannel(home, transport_key=secret, peers={pc.identity.device_id: pc.identity.public_key})
            client = LocalChannel(pc, transport_key=secret, peers={home.identity.device_id: home.identity.public_key})
            bank = pc.choices()["accounts"]["Bank"]
            category = next(value for label, value in pc.choices()["categories"].items() if label.startswith("Food"))
            samples = []
            for index in range(edits):
                started = time.monotonic()
                amount = f"-1.{index + 1:02d}" if index < 99 else "-2.00"
                pc.save(dict(money=dict(account=bank, other_account=None, date=today().isoformat(), amount=amount),
                    category=dict(category=category, splits=[]), details=dict(counterparty="", notes="", description="")))
                counters = dict(round_trips=0, uploaded=0, downloaded=0)
                async def request(wire):
                    response = server.handle(wire)
                    counters["round_trips"] += 1
                    counters["uploaded"] += len(wire)
                    counters["downloaded"] += len(response)
                    return response
                asyncio.run(client.synchronize(request, home_id=home.identity.device_id))
                samples.append(counters | dict(seconds=round(time.monotonic() - started, 4)))
            if home.store.fingerprint() != pc.store.fingerprint() or pc.store.pending():
                raise RuntimeError("Measurement did not converge")
            total = sum(sample["uploaded"] + sample["downloaded"] for sample in samples)
            return dict(domain="experimental base-currency cash services", edits=edits,
                converged=True, whole_file_baseline_bytes=baseline, total_delta_bytes=total,
                average_delta_bytes=round(total / edits),
                average_delta_to_one_whole_file=round(total / edits / baseline, 5),
                round_trips=sum(sample["round_trips"] for sample in samples),
                samples=samples, excludes="TLS/IP overhead, Android timing, internet billing and power-loss evidence")
        finally:
            for device in devices:
                device.store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edits", type=int, default=30)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = measure(args.edits)
    output = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "samples"}, indent=2))
