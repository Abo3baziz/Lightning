-- 0053 — gam'eya (rotating savings circle): a new account type and its terms.
-- accounts.account_type has a CHECK list that cannot be altered in place, so the table is rebuilt with
-- GAMEYA added. Foreign keys are deferred for the rebuild: the rows go back before the transaction ends.
PRAGMA defer_foreign_keys = ON;

CREATE TEMP TABLE _accounts_keep AS SELECT * FROM accounts;
DROP TABLE accounts;
CREATE TABLE accounts (
    id             INTEGER PRIMARY KEY,
    code           TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    institution    TEXT NOT NULL DEFAULT '',
    account_type   TEXT NOT NULL CHECK (account_type IN
                     ('CASH','BANK','DEPOSIT','BROKERAGE','PHYSICAL_ASSET','RECEIVABLE','OTHER_ASSET',
                      'CREDIT_CARD','LOAN','PAYABLE','GAMEYA')),
    currency       TEXT NOT NULL CHECK (length(currency) = 3),
    cash_class_id  INTEGER NOT NULL REFERENCES asset_classes(id),
    opening_date   TEXT NOT NULL CHECK (opening_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    is_system      INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    last4          TEXT CHECK (last4 IS NULL OR (length(last4) = 4 AND last4 GLOB '[0-9][0-9][0-9][0-9]')),
    active         INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sort_order     INTEGER NOT NULL DEFAULT 0,
    notes          TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    cash_at_hand   INTEGER NOT NULL DEFAULT 0 CHECK (cash_at_hand IN (0, 1))
);
CREATE INDEX ix_accounts_type ON accounts(account_type);
INSERT INTO accounts(id, code, name, institution, account_type, currency, cash_class_id, opening_date, is_system,
                     last4, active, sort_order, notes, created_at, updated_at, cash_at_hand)
SELECT id, code, name, institution, account_type, currency, cash_class_id, opening_date, is_system,
       last4, active, sort_order, notes, created_at, updated_at, cash_at_hand FROM _accounts_keep;
DROP TABLE _accounts_keep;

-- The asset class a circle's cash is reported under (also added by the seed on a new profile).
INSERT OR IGNORE INTO asset_classes(code, name, parent_id, sort_order, created_at, updated_at)
SELECT 'GAMEYA', 'Gam''eya paid in', NULL, COALESCE((SELECT MAX(sort_order) FROM asset_classes), 0) + 1,
       strftime('%Y-%m-%dT%H:%M:%S', 'now'), strftime('%Y-%m-%dT%H:%M:%S', 'now');

CREATE TABLE gameya_terms (
    account_id         INTEGER PRIMARY KEY REFERENCES accounts(id),
    organiser          TEXT NOT NULL DEFAULT '',
    members            INTEGER NOT NULL CHECK (members BETWEEN 2 AND 60),
    installment_e6     INTEGER NOT NULL CHECK (installment_e6 > 0),
    frequency          TEXT NOT NULL DEFAULT 'MONTHLY' CHECK (frequency IN ('MONTHLY')),
    first_date         TEXT NOT NULL CHECK (first_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    my_turn            INTEGER NOT NULL CHECK (my_turn >= 1),
    payout_e6          INTEGER NOT NULL CHECK (payout_e6 > 0),
    annual_rate        TEXT NOT NULL DEFAULT '0' CHECK (CAST(annual_rate AS REAL) BETWEEN 0 AND 100),
    funding_account_id INTEGER NOT NULL REFERENCES accounts(id),
    payout_account_id  INTEGER NOT NULL REFERENCES accounts(id),
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (my_turn <= members),
    CHECK (funding_account_id <> account_id AND payout_account_id <> account_id)
);
