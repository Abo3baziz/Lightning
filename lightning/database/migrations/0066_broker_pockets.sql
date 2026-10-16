-- A broker that trades in several currencies is one account on screen with one cash pocket per currency
-- (brokerage design 2026-10-15, owner decision 2026-10-16: one row per broker). A pocket is an ordinary
-- single-currency account whose parent_id names the broker; the broker account itself is the pocket of its own
-- currency, so every ledger rule keeps "one account line, one currency".
ALTER TABLE accounts ADD COLUMN parent_id INTEGER REFERENCES accounts(id);
CREATE INDEX idx_accounts_parent ON accounts(parent_id) WHERE parent_id IS NOT NULL;
