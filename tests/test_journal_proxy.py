"""J6f: the app's screens call services; on a journal profile covered writes become proposals."""
import pytest

from test_journal_finance import devices
from lightning.core.errors import ValidationError
from lightning.sync.journal.proxy import JournalServices, PendingOnHome


def test_home_screens_get_the_service_result_and_replicas_get_pending(devices):
    hd, pc = devices
    home, replica = JournalServices(hd), JournalServices(pc)
    created = home.account_flows.open_account("Savings", "BANK", "2026-02-01", "1,500.50")
    assert created.name == "Savings" and home.reporting.account_balance(created.id) == 1500.5
    with pytest.raises(PendingOnHome):
        replica.accounts.set_active(next(a.id for a in pc.c.accounts.list() if a.name == "Wallet"), False)
    pc.sync_with(hd.home)
    assert not next(a for a in pc.c.accounts.list() if a.name == "Wallet").active
    assert next(a for a in pc.c.accounts.list() if a.name == "Savings").id
    assert hd.store.fingerprint() == pc.store.fingerprint()


def test_a_refusal_reads_exactly_as_the_service_said_it(devices):
    hd, _ = devices
    with pytest.raises(ValidationError, match="already exists"):
        JournalServices(hd).account_flows.open_account("Bank", "BANK", "2026-02-01", "0")


def test_uncovered_options_and_writes_are_refused_not_written(devices):
    hd, _ = devices
    services = JournalServices(hd)
    with pytest.raises(ValidationError, match="not available"):
        services.account_flows.open_account("Euro", "BANK", "2026-02-01", "0", currency="EUR")
    with pytest.raises(hd.c.db.driver.DatabaseError):
        services.settings.set("uncovered", "write")
    assert services.accounts.get(next(a.id for a in hd.c.accounts.list() if a.name == "Bank")).name == "Bank"
