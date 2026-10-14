-- Instalment purchases and extra loan payments retain the original schedule and real cash history.
ALTER TABLE planned_items ADD COLUMN month_day INTEGER CHECK (month_day BETWEEN 1 AND 31);
CREATE TABLE installment_purchases (
    planned_item_id INTEGER PRIMARY KEY REFERENCES planned_items(id) ON DELETE CASCADE,
    price_e6 INTEGER NOT NULL CHECK (price_e6 > 0),
    fee_e6 INTEGER NOT NULL CHECK (fee_e6 >= 0),
    payment_count INTEGER NOT NULL CHECK (payment_count BETWEEN 1 AND 600)
);
CREATE TABLE loan_extra_payments (
    id INTEGER PRIMARY KEY,
    planned_item_id INTEGER NOT NULL REFERENCES planned_items(id),
    transaction_id INTEGER NOT NULL UNIQUE REFERENCES transactions(id),
    principal_e6 INTEGER NOT NULL CHECK (principal_e6 > 0),
    fee_e6 INTEGER NOT NULL CHECK (fee_e6 >= 0),
    due_date TEXT,
    created_at TEXT NOT NULL
);
