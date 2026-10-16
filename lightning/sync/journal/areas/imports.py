"""Bank-statement import: staged statements, their rows and the remembered column matches.

A statement travels as its file (at most 40 KiB) with the column matches; the home stages it and every staged
row is then an ordinary synchronized row. Confirming carries one decision per staged row, with the records the
decisions name (category, account, counterparty, owner, entry to link) as UUIDs.
"""
from .spec import BYTES, FLAG, JSON, TEXT, Command, optional, ref

TABLES = ("bank_import_batches", "bank_import_rows", "bank_import_column_maps")
BATCH = ("bank_import_batches", "batch_id")
IDS = {"category_id": "categories", "transfer_account_id": "accounts", "counterparty_id": "counterparties"}
CHOICES = {"counterparty_choice": ("existing:", "counterparties"), "owner_choice": ("existing:", "counterparties"),
           "match": ("link:", "transactions")}  # name -> (prefix of "<prefix><id>", table)


def _convert(decisions, row, one):
    """Every id-bearing field of every decision, and the row keys, through `row` and `one` (key and id converters)."""
    out = {}
    for key, decision in decisions.items():
        item = dict(decision)
        for name, table in IDS.items():
            if item.get(name) not in (None, ""):
                item[name] = one(table, item[name], True)
        for name, (prefix, table) in CHOICES.items():
            if isinstance(item.get(name), str) and item[name].startswith(prefix):
                item[name] = prefix + str(one(table, item[name][len(prefix):], False))
        out[row(key)] = item
    return out


def _encode(adapter, values):
    wire = _convert(values["decisions"], lambda key: adapter.uid("bank_import_rows", int(key)),
                    lambda table, value, whole: adapter.uid(table, int(value)))
    return values | dict(decisions=wire)


def _decode(adapter, values):
    # A whole-field id comes back as the type the form gave: counterparty_id an int, the others text.
    local = _convert(values["decisions"], lambda key: adapter.local("bank_import_rows", key),
                     lambda table, value, whole: adapter.local(table, value) if table == "counterparties" and whole
                     else str(adapter.local(table, value)))
    return values | dict(decisions=local)


COMMANDS = {
    "bank_imports.stage": Command("bank_imports.stage", dict(
        account_id=ref("accounts"), filename=TEXT, data=BYTES, mapping=optional(JSON), invert_amount=FLAG),
        creates="bank_import_batches"),
    "bank_imports.confirm": Command("bank_imports.confirm", dict(batch_id=ref("bank_import_batches"), decisions=JSON),
                                    target=BATCH, encode=_encode, decode=_decode),
    "bank_imports.discard": Command("bank_imports.discard", dict(batch_id=ref("bank_import_batches")), target=BATCH),
}
