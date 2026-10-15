"""Complete local financial records, for inspection and portability rather than profile restore."""
import csv
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from lightning.core.money import from_e6
from lightning.reporting.xlsx import MAX_ROWS, tabular_workbook_bytes

# Explicit financial-data boundary: passwords, pairing material, licences and runtime configuration
# are not exported. These are user records, including archived/voided items and unfinished reviews.
TABLES = ("profile_identity", "accounts", "asset_classes", "financial_assets", "categories", "counterparties",
          "counterparty_aliases", "institutions", "transactions", "ledger_entries", "registered_currencies", "currency_suggestions",
          "fx_rates", "price_history", "budgets", "budget_carryover", "budget_carryover_resets", "cash_reserves",
          "reserve_allocation_history", "reserve_transaction_links", "planned_items", "planned_payments",
          "loan_extra_payments", "installment_purchases", "cd_terms", "cd_certificates", "cd_redemptions",
          "gameya_terms", "money_from_others", "investment_custody_events", "investment_dividend_assets",
          "investment_liquidation_factors", "investment_targets", "physical_items", "physical_item_valuations",
          "physical_item_trade_details", "other_asset_valuations", "rules", "rule_conditions", "rule_actions",
          "bank_import_batches", "bank_import_rows", "bank_import_column_maps", "reevaluation_periods",
          "reevaluation_entries", "reevaluation_account_posts", "reevaluation_suppressed_accounts", "zakat_settings",
          "reconciled_through", "saved_views", "reimbursement_claims", "reimbursement_receipts",
          "cd_interest_receipt_events", "cd_interest_receipt_links", "cash_funding", "audit_log")


def _safe_text(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def export_tables(c):
    tables = []
    # One consistent read snapshot, with no plaintext files on disk.
    with c.db.read_snapshot():
        present = {row["name"] for row in c.db.all("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in (*TABLES, "settings"):
            if name not in present:
                continue
            columns = [row["name"] for row in c.db.all(f'PRAGMA table_info("{name}")')]
            rows = c.db.all(f'SELECT * FROM "{name}" ORDER BY rowid')
            if name == "settings":
                rows = [row for row in rows if row["key"] in ("base_currency", "locale", "privacy_mode")
                        or row["key"].startswith(("budget_", "investment_", "emergency_", "health_", "financial_health_"))]
            headings = [column.removesuffix("_e6") for column in columns]
            values = [tuple(from_e6(row[col]) if col.endswith("_e6") and row[col] is not None else row[col]
                            for col in columns) for row in rows]
            tables.append((name, headings, values, [22] * len(columns)))
    return tables


def export_all(c, format):
    tables = export_tables(c)
    if format == "xlsx":
        sheets = []
        for name, headings, rows, widths in tables:
            parts = max(1, (len(rows) + MAX_ROWS - 2) // (MAX_ROWS - 1))
            for part in range(parts):
                suffix = f"_{part + 1}" if parts > 1 else ""
                sheet_name = name[:31 - len(suffix)] + suffix
                sheets.append((sheet_name, headings, rows[part * (MAX_ROWS - 1):(part + 1) * (MAX_ROWS - 1)], widths))
        return tabular_workbook_bytes(sheets), "lightning-all-data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if format != "csv":
        raise ValueError("Choose Excel or CSV.")
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, headings, rows, _ in tables:
            buffer = StringIO(newline="")
            writer = csv.writer(buffer)
            writer.writerow(headings)
            writer.writerows(tuple(_safe_text(value) for value in row) for row in rows)
            archive.writestr(name + ".csv", "\ufeff" + buffer.getvalue())
        archive.writestr("README.txt", "Lightning financial data\nAll dates and IDs are preserved. Money and quantities are decoded from millionths to decimal values.\nIncludes archived and voided records and unfinished statement reviews. CSV text that could be a spreadsheet formula is prefixed with an apostrophe.\nSecurity credentials are excluded. These unencrypted inspection files are not profile backups; use Back up now to restore a profile.\n")
    return output.getvalue(), "lightning-all-data.zip", "application/zip"
