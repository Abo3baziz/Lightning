"""Master data: accounts and categories."""
from .spec import AMOUNT, DATE, FLAG, LONG, TEXT, Command, choice, optional, ref

TABLES = ("asset_classes", "financial_assets", "accounts", "categories")

ACCOUNT_TYPES = choice("BANK", "CASH", "CASH_AT_HAND")
COMMANDS = {
    "accounts.open": Command("account_flows.open_account", dict(
        name=TEXT, account_type=ACCOUNT_TYPES, opening_date=DATE, opening_balance=AMOUNT, institution=TEXT,
        last4=optional(TEXT), notes=LONG), creates="accounts"),
    "accounts.update": Command("accounts.update", dict(
        account_id=ref("accounts"), name=TEXT, institution=TEXT, account_type=ACCOUNT_TYPES, opening_date=DATE,
        last4=optional(TEXT), notes=LONG), target=("accounts", "account_id")),
    "accounts.set_active": Command("accounts.set_active", dict(account_id=ref("accounts"), active=FLAG),
                                   target=("accounts", "account_id")),
    # The account screens call the workflow layer.
    "account_flows.update_account": Command("account_flows.update_account", dict(
        account_id=ref("accounts"), name=TEXT, account_type=ACCOUNT_TYPES, opening_date=DATE, opening_balance=AMOUNT,
        institution=TEXT, last4=optional(TEXT), notes=LONG, opening_balance_date=optional(DATE),
        owner_id=optional(ref("counterparties"))), target=("accounts", "account_id")),
    "account_flows.deactivate": Command("account_flows.deactivate", dict(account_id=ref("accounts")),
                                        target=("accounts", "account_id")),
    "account_flows.reactivate": Command("account_flows.reactivate", dict(account_id=ref("accounts")),
                                        target=("accounts", "account_id")),
    "categories.create": Command("categories.create", dict(
        parent_id=ref("categories"), name=TEXT, default_reimbursable=optional(FLAG)), creates="categories"),
    "categories.update": Command("categories.update", dict(
        category_id=ref("categories"), name=TEXT, active=FLAG, default_reimbursable=optional(FLAG)),
        target=("categories", "category_id")),
}
