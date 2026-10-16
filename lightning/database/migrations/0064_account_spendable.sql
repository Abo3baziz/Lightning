-- Whether an account's own cash counts as spendable (Free cash, Safe to spend, the payday pool).
-- NULL follows the default: wallets and bank accounts in the profile currency count; brokerage cash and
-- foreign-currency cash are kept apart (audit 2026-10-15). 1 or 0 is the person's own choice.
ALTER TABLE accounts ADD COLUMN spendable INTEGER;
