"""Physical items (gold pieces and the like): the item, its dated valuations and the workmanship note of a trade.

A purchase or sale is the investment trade plus `physical.record_trade_details`; the screen sends them as two
commands, so on another device only the trade is saved until the home confirms it.
"""
from .spec import AMOUNT, DATE, FLAG, INT, LONG, RATE, TEXT, Command, choice, optional, ref

TABLES = ("physical_items", "physical_item_valuations", "physical_item_trade_details")
# These name an item by its asset id, which their foreign key declares against `physical_items` (no `id` column).
REFS = {"physical_item_valuations": {"asset_id": "financial_assets"},
        "physical_item_trade_details": {"asset_id": "financial_assets"}}

ITEM = dict(name=TEXT, kind=TEXT, grams_per_piece=RATE, karat=INT, reference_asset_id=ref("financial_assets"), details=LONG)
COMMANDS = {
    # The service returns the item's asset id, which is also the item's identity.
    "physical.create": Command("physical_items.create", dict(account_id=ref("accounts"), **ITEM, worn=FLAG),
                               creates="financial_assets"),
    "physical.update": Command("physical_items.update", dict(asset_id=ref("financial_assets"), **ITEM, worn=optional(FLAG)),
                               target=("financial_assets", "asset_id")),
    "physical.record_valuation": Command("physical_items.record_valuation", dict(
        asset_id=ref("financial_assets"), day=DATE, total_value=AMOUNT, notes=LONG)),
    "physical.record_trade_details": Command("physical_items.record_trade_details", dict(
        transaction_id=ref("transactions"), asset_id=ref("financial_assets"), action=choice("BUY", "SEL", "OPN"),
        workmanship_cost=optional(AMOUNT), notes=LONG), adapt=lambda values: values | dict(
            workmanship_cost=values["workmanship_cost"] or "0")),
}
