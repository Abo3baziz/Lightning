-- Whether an account's own cash counts as spendable (Free cash, Safe to spend, the payday pool).
-- NULL follows the default: wallets and bank accounts in the profile currency count; brokerage cash and
-- foreign-currency cash are kept apart (audit 2026-10-15). 1 or 0 is the person's own choice.
ALTER TABLE accounts ADD COLUMN spendable INTEGER;

-- Dinars and the Omani rial have three minor units (ISO 4217): 1.250 KWD must be enterable.
UPDATE financial_assets SET quantity_decimals = 3
 WHERE is_cash = 1 AND currency IN ('KWD', 'BHD', 'OMR', 'JOD', 'TND', 'LYD', 'IQD') AND quantity_decimals < 3;
