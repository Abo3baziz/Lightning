-- Keep one statement row per transaction within a batch, while allowing a later
-- statement from another source to add provenance to the same ledger entry.
DROP INDEX ux_bank_import_transaction;
CREATE UNIQUE INDEX ux_bank_import_transaction_batch
    ON bank_import_rows(batch_id, transaction_id, account_id)
    WHERE status IN ('POSTED','LINKED');
