-- Explicit, reversible reconciliation of expected CD interest with already-posted bank receipts.
CREATE TABLE cd_interest_receipt_events (
    id                     INTEGER PRIMARY KEY,
    certificate_id         INTEGER NOT NULL REFERENCES cd_certificates(id) ON DELETE CASCADE,
    event_date             TEXT NOT NULL CHECK (event_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    destination_account_id INTEGER NOT NULL REFERENCES accounts(id),
    expected_amount_e6     INTEGER NOT NULL CHECK (expected_amount_e6 > 0),
    created_at             TEXT NOT NULL,
    UNIQUE(certificate_id,event_date)
);

CREATE TABLE cd_interest_receipt_links (
    id               INTEGER PRIMARY KEY,
    event_id         INTEGER NOT NULL REFERENCES cd_interest_receipt_events(id) ON DELETE CASCADE,
    transaction_id   INTEGER NOT NULL UNIQUE REFERENCES transactions(id),
    amount_e6        INTEGER NOT NULL CHECK (amount_e6 > 0),
    transaction_date TEXT NOT NULL,
    linked_at        TEXT NOT NULL
);
CREATE INDEX ix_cd_interest_receipt_event ON cd_interest_receipt_links(event_id,id);
