CREATE TABLE cash_funding (
    month TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount_e6 INTEGER NOT NULL CHECK(amount_e6>=0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY(month,category_id)
);
CREATE TRIGGER reimbursement_receipt_exclusive BEFORE INSERT ON reimbursement_receipts
WHEN EXISTS(SELECT 1 FROM cd_interest_receipt_links WHERE transaction_id=NEW.receipt_id)
BEGIN SELECT RAISE(ABORT,'This receipt is already matched to certificate interest.'); END;
CREATE TRIGGER cd_receipt_exclusive BEFORE INSERT ON cd_interest_receipt_links
WHEN EXISTS(SELECT 1 FROM reimbursement_receipts WHERE receipt_id=NEW.transaction_id)
BEGIN SELECT RAISE(ABORT,'This receipt is already linked to a reimbursement claim.'); END;
