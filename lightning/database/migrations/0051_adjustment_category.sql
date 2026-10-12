-- 0051 — a catch-all category for entries that genuinely need an adjustment.
-- Skipped when a newer seed already holds EXP.SYSTEM.ADJUSTMENT (0052 moves it there).
-- Capital allocations remain transfers between own accounts, so they are never income or spending.
INSERT INTO categories(code,name,parent_id,movement,scope,income_class,family,
                       default_reimbursable,is_system,active,sort_order,direction,created_at,updated_at)
SELECT 'EXP.PERSONAL.ADJUSTMENT','Adjustment',id,'OUTFLOW','PERSONAL',NULL,'PERSONAL',
       0,0,1,91,'BOTH',datetime('now'),datetime('now')
FROM categories
WHERE code='EXP.PERSONAL'
  AND NOT EXISTS (SELECT 1 FROM categories WHERE code IN ('EXP.PERSONAL.ADJUSTMENT','EXP.SYSTEM.ADJUSTMENT'));
