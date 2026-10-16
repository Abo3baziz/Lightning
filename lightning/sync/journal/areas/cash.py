"""Cash register. The journal's own register uses field groups (`finance.CashAdapter`);
the app's screens send these commands, preconditioned on the transaction row."""
from .spec import AMOUNT, DATE, LONG, TEXT, Command, items, listof, optional, ref

TABLES = ("counterparties", "transactions", "ledger_entries")
REGISTER = dict(account_id=ref("accounts"), date=DATE, amount=AMOUNT, category_id=optional(ref("categories")),
                other_account_id=optional(ref("accounts")), counterparty=TEXT, notes=LONG,
                owner_id=optional(ref("counterparties")))
TXN = ("transactions", "txn_id")
COMMANDS = {
    "transactions.record_in_account": Command("transactions.record_in_account", REGISTER | dict(description=TEXT),
                                              creates="transactions"),
    "transactions.update_in_account": Command("transactions.update_in_account", dict(txn_id=ref("transactions")) | REGISTER,
                                              target=TXN),
    "transactions.update_metadata": Command("transactions.update_metadata", dict(
        txn_id=ref("transactions"), date=DATE, counterparty=TEXT, notes=LONG), target=TXN),
    "transactions.update_expense_split": Command("transactions.update_expense_split", dict(
        txn_id=ref("transactions"), allocations=items(category_id=ref("categories"), amount=AMOUNT)), target=TXN,
        adapt=lambda values: values | dict(allocations=[(line["category_id"], line["amount"]) for line in values["allocations"]])),
    "transactions.void": Command("transactions.void", dict(txn_id=ref("transactions"), reason=TEXT), target=TXN),
    "transactions.restore": Command("transactions.restore", dict(txn_id=ref("transactions")), target=TXN),
    # Bulk actions on a selection carry no single-row precondition.
    "transactions.delete_many": Command("transactions.delete_many", dict(txn_ids=listof(ref("transactions")))),
    "transactions.set_category": Command("transactions.set_category", dict(
        txn_ids=listof(ref("transactions")), category_id=ref("categories"))),
}
