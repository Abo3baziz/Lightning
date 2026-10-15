CREATE TABLE reconciled_through (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
    date TEXT NOT NULL,
    bank_balance_e6 INTEGER NOT NULL,
    checked_at TEXT NOT NULL
);
CREATE TRIGGER checked_ledger_insert BEFORE INSERT ON ledger_entries
WHEN EXISTS(SELECT 1 FROM reconciled_through r WHERE r.account_id=NEW.account_id AND NEW.date<=r.date)
BEGIN SELECT RAISE(ABORT,'This month was checked against the bank. Unlock it first.'); END;
CREATE TRIGGER checked_ledger_update BEFORE UPDATE ON ledger_entries
WHEN EXISTS(SELECT 1 FROM reconciled_through r WHERE (r.account_id=OLD.account_id AND OLD.date<=r.date)
    OR (r.account_id=NEW.account_id AND NEW.date<=r.date))
BEGIN SELECT RAISE(ABORT,'This month was checked against the bank. Unlock it first.'); END;
CREATE TRIGGER checked_ledger_delete BEFORE DELETE ON ledger_entries
WHEN EXISTS(SELECT 1 FROM reconciled_through r WHERE r.account_id=OLD.account_id AND OLD.date<=r.date)
BEGIN SELECT RAISE(ABORT,'This month was checked against the bank. Unlock it first.'); END;
CREATE TRIGGER checked_transaction_update BEFORE UPDATE ON transactions
WHEN EXISTS(SELECT 1 FROM ledger_entries le JOIN reconciled_through r ON r.account_id=le.account_id
    WHERE le.transaction_id=OLD.id AND le.date<=r.date)
BEGIN SELECT RAISE(ABORT,'This month was checked against the bank. Unlock it first.'); END;
CREATE TRIGGER checked_transaction_delete BEFORE DELETE ON transactions
WHEN EXISTS(SELECT 1 FROM ledger_entries le JOIN reconciled_through r ON r.account_id=le.account_id
    WHERE le.transaction_id=OLD.id AND le.date<=r.date)
BEGIN SELECT RAISE(ABORT,'This month was checked against the bank. Unlock it first.'); END;
