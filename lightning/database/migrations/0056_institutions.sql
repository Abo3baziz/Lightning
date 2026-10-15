-- Institutions a person adds beside the built-in list of Egypt's banks, brokers and wallets
-- (lightning/accounts/institutions.csv). accounts.institution stays plain text.
CREATE TABLE institutions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
