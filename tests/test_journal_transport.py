"""Transport cost over the mailbox: wake cycles, held uploads, refused envelopes, reply size."""
import asyncio
import os

import pytest

from test_journal_cloud import Carrier, peers
from test_journal_finance import devices, groups  # noqa: F401  (devices is a fixture)
from lightning.sync.journal import local
from lightning.sync.journal.cloud import CloudUnavailable, MailboxExchange, ReplyPending, RetryWindow
from lightning.sync.journal.codec import MAX_MESSAGE, JournalError, seal, unpack
from lightning.sync.journal.local import UploadHeld, encode


async def wakes(hp, pp, home_id, done, limit=40):
    """One device wake (one synchronize) then one home wake (two pumps), as JournalInternet does."""
    for cycle in range(1, limit + 1):
        try:
            await pp.channel.synchronize(MailboxExchange(pp), home_id=home_id, max_requests=20)
        except ReplyPending:
            pass
        except CloudUnavailable:
            pytest.fail("Waiting for the home must be ReplyPending, not a carrier failure")
        await hp.pump()
        await hp.pump()
        if done():
            return cycle
    pytest.fail("Did not converge")


@pytest.mark.parametrize("edits,limit", [(1, 3), (10, 4), (20, 6)])
def test_offline_edits_converge_in_few_wake_cycles(devices, edits, limit):
    home, pc = devices
    hp, pp = peers(devices, Carrier())
    for index in range(edits):
        pc.save(groups(pc, f"-{index + 1}.00"))
    cycles = asyncio.run(wakes(hp, pp, home.identity.device_id, lambda: not pc.store.pending() and pc.store.cursor() == home.store.cursor()))
    print(f"{edits} offline edits: {cycles} cycles")
    assert cycles <= limit
    assert home.store.fingerprint() == pc.store.fingerprint()


def test_thirty_home_commits_reach_the_pc_in_four_cycles(devices):
    home, pc = devices
    hp, pp = peers(devices, Carrier())
    for index in range(30):
        home.save(groups(home, f"-{index + 1}.00"))
    cycles = asyncio.run(wakes(hp, pp, home.identity.device_id, lambda: pc.store.cursor() == home.store.cursor()))
    print(f"30 home commits: {cycles} cycles")
    assert cycles <= 4 and pc.store.fingerprint() == home.store.fingerprint()


def test_more_than_one_batch_of_proposals_needs_few_requests(devices):
    home, pc = devices
    channels = peers(devices, Carrier())
    for index in range(60):
        pc.save(groups(pc, f"-{index + 1}.00"))
    count = 0
    async def request(wire):
        nonlocal count
        count += 1
        return channels[0].channel.handle(wire)
    asyncio.run(channels[1].channel.synchronize(request, home_id=home.identity.device_id))
    assert count <= 5 and not pc.store.pending()
    assert home.store.fingerprint() == pc.store.fingerprint()


def test_a_refused_upload_still_downloads_and_keeps_the_edit_pending(devices, monkeypatch):
    home, pc = devices
    hp, pp = peers(devices, Carrier())
    home.save(groups(home, "-3.00"))
    pc.save(groups(pc, "-1.00"))
    pc.save(groups(pc, "-2.00"))
    receive, calls = home.home.receive, []
    def refuse_second(wire):
        calls.append(wire)
        if len(calls) == 2:
            raise JournalError("Sequence gap exceeds staging window")
        return receive(wire)
    monkeypatch.setattr(home.home, "receive", refuse_second)
    async def request(wire):
        return hp.channel.handle(wire)
    with pytest.raises(UploadHeld, match="staging window"):
        asyncio.run(pp.channel.synchronize(request, home_id=home.identity.device_id))
    assert pc.store.cursor() == home.store.cursor() and pc.store.cursor()["revision"] == 2
    assert len(pc.store.pending()) == 1
    monkeypatch.undo()
    asyncio.run(pp.channel.synchronize(request, home_id=home.identity.device_id))
    assert not pc.store.pending() and pc.store.fingerprint() == home.store.fingerprint()


def test_pending_reply_is_waiting_not_failure():
    now = [0]
    retry = RetryWindow(clock=lambda: now[0], jitter=lambda _: 0)
    for _ in range(5):
        retry.result(False)
    retry.waiting()
    assert retry.failures == 0 and retry.next_attempt == 30
    retry.waiting()
    assert retry.next_attempt == 30
    assert issubclass(ReplyPending, CloudUnavailable)


def test_unopenable_envelope_is_recorded_acknowledged_and_does_not_block_the_next(devices):
    home, pc = devices
    carrier = Carrier()
    hp, pp = peers(devices, carrier)
    exchange = MailboxExchange(pp)
    wire = exchange.prepare(dict(operation="capabilities", value=None), home.identity.device_id)
    body = unpack(wire)["body"]
    body["ciphertext"] = encode(os.urandom(40))  # Correctly signed by a member, but not decryptable.
    body["nonce"] = os.urandom(12).hex()
    bad = seal(body, pc.identity.sign)
    pp.enqueue(bad)
    async def run():
        with pytest.raises(ReplyPending):
            await exchange(wire)
        await hp.pump()
        assert not [key for key in carrier.messages if key[0] == home.identity.device_id]  # Both acknowledged.
        await hp.pump()
        await pp.pump()
        assert await exchange(wire)
    asyncio.run(run())
    assert hp.db.scalar("SELECT COUNT(*) FROM journal_mail_in WHERE processed=2") == 1
    assert hp.db.scalar("SELECT COUNT(*) FROM journal_mail_in WHERE processed=0") == 0


def reply_for(devices, monkeypatch, sizes):
    home, pc = devices
    hp, pp = peers(devices, Carrier())
    monkeypatch.setattr(home.store, "commits_after", lambda cursor, limit=50: [os.urandom(size) for size in sizes])
    request = pp.channel.protect(dict(operation="round", value=dict(capabilities=local_caps(pc), proposals=[], status=[], cursor=pc.store.cursor())), home.identity.device_id)
    answer = hp.channel.handle(request)
    _, payload = pp.channel.open(answer)
    return answer, payload["result"]["commits"]


def local_caps(device):
    from lightning.sync.journal.compatibility import capabilities
    return capabilities(device.store)


def test_the_largest_commit_a_reply_can_carry_fits_and_extras_are_left_for_the_next_round(devices, monkeypatch):
    answer, commits = reply_for(devices, monkeypatch, [33 * 1024])
    assert len(commits) == 1 and len(answer) <= MAX_MESSAGE
    answer, commits = reply_for(devices, monkeypatch, [20 * 1024] * 3)
    assert 1 <= len(commits) < 3 and len(answer) <= MAX_MESSAGE
    monkeypatch.setattr(local, "REPLY_BUDGET", 10**9)  # Even without the soft budget, the seal bound trims.
    answer, commits = reply_for(devices, monkeypatch, [30 * 1024] * 3)
    assert len(commits) == 1 and len(answer) <= MAX_MESSAGE
    with pytest.raises(JournalError, match="size"):  # Documented bound: about 35 KiB of commit wire.
        reply_for(devices, monkeypatch, [40 * 1024])


def test_catch_up_waiting_for_the_home_does_not_back_off(devices):
    from lightning.runtime.journal_internet import JournalInternet
    from lightning.sync.journal.membership import Membership
    home, pc = devices
    members = {d.identity.device_id: dict(key=d.identity.public_key, incarnation=d.store.config["incarnation"]) for d in devices}
    secret = os.urandom(32)
    for device in devices:
        Membership(device).initialize(members, secret)
    carrier = Carrier()
    hr = JournalInternet(home, "https://configured.example", client=carrier.client(home))
    pr = JournalInternet(pc, "https://configured.example", client=carrier.client(pc))
    pc.save(groups(pc))
    async def run():
        for _ in range(3):
            assert not await pr.catch_up(foreground=True)  # Home asleep: waiting.
            assert pr.retry.failures == 0
        await hr.catch_up(foreground=True)
        assert await pr.catch_up(foreground=True)
        assert not pc.store.pending()
        await hr.close()
        await pr.close()
    asyncio.run(run())
