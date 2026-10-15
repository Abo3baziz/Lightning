CREATE TABLE reimbursement_claims (
    id              INTEGER PRIMARY KEY,
    expense_id      INTEGER UNIQUE REFERENCES transactions(id) ON DELETE SET NULL,
    expected_e6     INTEGER NOT NULL CHECK (expected_e6 > 0),
    payer_id        INTEGER REFERENCES counterparties(id) ON DELETE SET NULL,
    due_date        TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX ix_reimbursement_claims_due ON reimbursement_claims(due_date, id);

CREATE TABLE reimbursement_receipts (
    id              INTEGER PRIMARY KEY,
    claim_id        INTEGER NOT NULL REFERENCES reimbursement_claims(id) ON DELETE CASCADE,
    receipt_id      INTEGER UNIQUE REFERENCES transactions(id) ON DELETE SET NULL,
    amount_e6       INTEGER NOT NULL CHECK (amount_e6 > 0),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX ix_reimbursement_receipts_claim ON reimbursement_receipts(claim_id, id);
