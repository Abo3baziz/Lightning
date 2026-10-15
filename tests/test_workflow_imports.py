from __future__ import annotations


def _stage(c, account_id, filename, text):
    batch_id, _ = c.bank_imports.stage(account_id, filename, text.encode())
    return batch_id, c.bank_imports.preview(batch_id)[1]


def test_same_transaction_accepts_second_source_once_and_repeat_defaults_to_skip(c, setup):
    accounts, cats = setup
    account_id = accounts["cib"].id
    manual = c.transactions.record_outflow("2026-10-05", account_id, "45", cats["EXP.PERSONAL.FOOD"].id,
                                           counterparty="Kiosk")
    balance = c.reporting.account_balance(account_id)

    first_id, first_rows = _stage(c, account_id, "statement.csv",
                                  "Date,Counterparty,Amount\n2026-10-05,Kiosk,-45\n")
    first_row = first_rows[0]
    first = c.bank_imports.confirm(first_id, {
        first_row["_import_row_id"]: {"match": f"link:{manual.id}"}})
    assert first["linked"] == 1 and first["posted"] == 0 and not first["errors"]
    assert c.reporting.account_balance(account_id) == balance

    second_id, second_rows = _stage(c, account_id, "sms-export.csv",
                                   "Date,Counterparty,Amount,Notes\n2026-10-05,Kiosk,-45,bank notification\n")
    second = second_rows[0]
    assert [candidate["id"] for candidate in second["_link_candidates"]] == [manual.id]
    assert second["_link_candidates"][0]["source_count"] == 1
    assert second["_link_candidates"][0]["source_files"] == "statement.csv"
    assert second["_default_match"] == "skip"
    linked = c.bank_imports.confirm(second_id, {
        second["_import_row_id"]: {"match": f"link:{manual.id}"}})
    assert linked["linked"] == 1 and linked["posted"] == 0 and not linked["errors"]
    assert c.reporting.account_balance(account_id) == balance
    assert c.db.scalar("SELECT COUNT(*) FROM bank_import_rows WHERE transaction_id=? AND status='LINKED'",
                       (manual.id,)) == 2

    repeat_id, repeat_rows = _stage(c, account_id, "sms-export-again.csv",
                                    "Date,Counterparty,Amount,Notes\n2026-10-05,Kiosk,-45,bank notification\n")
    repeat = repeat_rows[0]
    assert repeat["_default_match"] == "skip"
    skipped = c.bank_imports.confirm(repeat_id, {repeat["_import_row_id"]: {"match": "skip"}})
    assert skipped["duplicates"] == 1 and not skipped["errors"]
    assert c.reporting.account_balance(account_id) == balance
