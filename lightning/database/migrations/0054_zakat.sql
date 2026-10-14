-- 0054 — zakat: one settings row, a "worn" flag on physical gold pieces, and the Zakat spending category.
-- Zakat is an estimate by the common rule; nothing here moves money. A payment is ordinary spending in Zakat.
CREATE TABLE zakat_settings (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    zakat_day         TEXT,                                   -- yyyy-mm-dd, the day the user picked; each next is +354 days
    typed_nisab_e6    INTEGER CHECK (typed_nisab_e6 IS NULL OR typed_nisab_e6 > 0),  -- used only when no gold price is known
    typed_nisab_date  TEXT,                                   -- the day the user typed it
    count_worn_gold   INTEGER NOT NULL DEFAULT 0 CHECK (count_worn_gold IN (0, 1)),
    deduct_debts_due  INTEGER NOT NULL DEFAULT 1 CHECK (deduct_debts_due IN (0, 1)),
    updated_at        TEXT NOT NULL
);
INSERT INTO zakat_settings(id, updated_at) VALUES (1, datetime('now'));

ALTER TABLE physical_items ADD COLUMN worn INTEGER NOT NULL DEFAULT 0 CHECK (worn IN (0, 1));

INSERT INTO categories(code,name,parent_id,movement,scope,income_class,family,
                       default_reimbursable,is_system,active,sort_order,direction,created_at,updated_at)
SELECT 'EXP.SYSTEM.ZAKAT','Zakat',id,'OUTFLOW','PERSONAL',NULL,'PERSONAL',
       0,0,1,95,NULL,datetime('now'),datetime('now')
FROM categories
WHERE code='EXP.SYSTEM'
  AND NOT EXISTS (SELECT 1 FROM categories WHERE code='EXP.SYSTEM.ZAKAT');
