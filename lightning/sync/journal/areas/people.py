"""People: counterparty names and aliases, money held for others."""
from .spec import AMOUNT, DATE, LONG, TEXT, Command, optional, ref

TABLES = ("counterparty_aliases", "money_from_others")
CUSTODY = dict(transaction_id=ref("transactions"), day=DATE, owner=optional(TEXT), amount=AMOUNT, notes=LONG)
COMMANDS = {
    "counterparties.add_alias": Command("counterparties.add_alias", dict(counterparty_id=ref("counterparties"), alias=TEXT),
                                        target=("counterparties", "counterparty_id")),
    # Returns an existing person or a new one, so it binds nothing and has no precondition.
    "counterparties.ensure_person": Command("counterparties.ensure_person", dict(name=TEXT)),
    "money_from_others.sync_transaction": Command("money_from_others.sync_transaction",
                                                  CUSTODY | dict(account_id=ref("accounts"))),
    "money_from_others.sync_transfer": Command("money_from_others.sync_transfer",
                                               CUSTODY | dict(source_id=ref("accounts"), target_id=ref("accounts"))),
}
