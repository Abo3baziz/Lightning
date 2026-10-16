-- A counterparty is a PERSON (can hold money or things for you), a BUSINESS (a shop, an employer), or
-- not yet said (NULL). Owner pickers list people only. Every counterparty already used as an owner is a person.
ALTER TABLE counterparties ADD COLUMN kind TEXT CHECK (kind IN ('PERSON','BUSINESS'));
UPDATE counterparties SET kind='PERSON' WHERE id IN (
    SELECT owner_id FROM ledger_entries WHERE owner_id IS NOT NULL
    UNION SELECT owner_id FROM reevaluation_entries WHERE owner_id IS NOT NULL
    UNION SELECT c2.id FROM counterparties c2 JOIN money_from_others m ON m.owner=c2.name AND trim(m.owner)<>''
);
