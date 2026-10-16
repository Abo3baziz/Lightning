-- Investment › Tax withheld: tax a broker takes off a dividend before paying it. An investment-family
-- outflow, so it is never budget spending and never household Money out.
INSERT INTO categories(code,name,parent_id,movement,scope,income_class,family,default_reimbursable,is_system,active,sort_order,created_at,updated_at)
SELECT 'EXP.INVEST.TAX','Tax withheld',id,'OUTFLOW',NULL,NULL,'INVESTMENT',0,0,1,3,datetime('now'),datetime('now')
FROM categories WHERE code='EXP.INVEST'
  AND NOT EXISTS (SELECT 1 FROM categories WHERE code='EXP.INVEST.TAX');
