"""Zakat: an estimate by the common rule, never a ruling (Architecture › Zakat).

Zakat due = 2.5% of zakatable wealth when it is at or above the nisab on your zakat day. Everything is read
from the one position calculation (`planning/position.py`), never re-added from balances; money held for
others is never in it. Nothing here moves money: a payment is ordinary spending in the Zakat category.

    Zakatable wealth = Cash you own + Deposits + Shares and funds + Gold held as savings
                       (+ Gold you wear, by the setting) (− Debts due now, by the setting)
    Nisab            = 85 g of 24K gold × the gold price that day, else the nisab the user typed
    Zakat due        = 2.5% × Zakatable wealth, when Zakatable wealth ≥ Nisab, else 0
    Still to pay     = Zakat due − Paid this zakat year, never below 0

The zakat year follows the lunar calendar: the user picks a date once and each next zakat day is 354 days later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from lightning.core.dates import fmt_date, now_iso, parse_date, today
from lightning.core.errors import ValidationError
from lightning.core.figures import label
from lightning.core.money import ONE, ZERO, check_places, from_e6, to_decimal, to_e6

ZAKAT_CATEGORY = "EXP.SYSTEM.ZAKAT"
LUNAR_YEAR_DAYS = 354
NISAB_GRAMS = Decimal(85)
ZAKAT_RATE = Decimal("0.025")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class ZakatSettings:
    zakat_day: str | None
    typed_nisab: Decimal | None
    typed_nisab_date: str | None
    count_worn_gold: bool
    deduct_debts_due: bool


@dataclass(frozen=True)
class ZakatLine:
    """One line of the list. `amount` is always positive; a line with `minus` is taken off. A line that is not
    `counted` is shown (so you see why it is not in the total) and left out of Zakatable wealth."""
    key: str
    label: str
    amount: Decimal
    counted: bool = True
    minus: bool = False

    @property
    def signed(self) -> Decimal:
        if not self.counted:
            return ZERO
        return -self.amount if self.minus else self.amount


@dataclass(frozen=True)
class Assessment:
    as_of: str
    settings: ZakatSettings
    zakat_day: str | None          # the next zakat day on or after as_of; None until the user picks one
    previous_day: str | None       # the zakat day before it: this zakat year starts the day after
    lines: tuple[ZakatLine, ...]
    zakatable_wealth: Decimal
    nisab: Decimal | None
    nisab_source: str              # "gold" (85 g at that day's price), "typed" or "" when there is none
    nisab_date: str | None         # the day of the gold price, or the day the nisab was typed
    zakat_due: Decimal | None      # None when the estimate cannot be made; the reason is in `unavailable_reason`
    paid: Decimal | None           # None until a zakat day is set
    still_to_pay: Decimal | None
    unavailable_reason: str = ""

    @property
    def reaches_nisab(self) -> bool | None:
        return None if self.nisab is None else self.zakatable_wealth >= self.nisab


@dataclass(frozen=True)
class ZakatForecast:
    """The line Cash planning draws: the next zakat day and what is still to pay by then, at today's figures."""
    day: str
    amount: Decimal


def zakat_days(first_day: str | None, on: date) -> tuple[date, date] | None:
    """(previous, next) zakat days around `on`. The next is the first zakat day on or after `on`: the day the
    user picked, then every 354 days (a lunar year) after it. None until a day is picked."""
    if not first_day:
        return None
    first = parse_date(first_day)
    if on <= first:
        following = first
    else:
        years = -(-(on - first).days // LUNAR_YEAR_DAYS)  # whole lunar years, rounded up
        following = first + timedelta(days=years * LUNAR_YEAR_DAYS)
    return following - timedelta(days=LUNAR_YEAR_DAYS), following


class ZakatService:
    def __init__(self, db, position, reporting, assets, categories, physical_items, audit):
        self.db, self.position, self.reporting, self.assets = db, position, reporting, assets
        self.categories, self.physical_items, self.audit = categories, physical_items, audit

    # ------------------------------------------------------------ settings
    def settings(self) -> ZakatSettings:
        row = self.db.one("SELECT * FROM zakat_settings WHERE id=1")
        if row is None:  # a profile older than migration 0054 cannot reach here, but never fail a page for it
            return ZakatSettings(None, None, None, False, True)
        return ZakatSettings(row["zakat_day"], from_e6(row["typed_nisab_e6"]) if row["typed_nisab_e6"] else None,
                             row["typed_nisab_date"], bool(row["count_worn_gold"]), bool(row["deduct_debts_due"]))

    def save_settings(self, zakat_day: str | None, typed_nisab, count_worn_gold: bool, deduct_debts_due: bool) -> None:
        """Save the settings. An empty zakat day or nisab clears it; a typed nisab is kept with today's date
        (and keeps its old date when it is unchanged)."""
        old = self.settings()
        day = str(zakat_day or "").strip()
        if day:
            day = fmt_date(parse_date(day, "zakat day"))
        text = str(typed_nisab if typed_nisab is not None else "").strip()
        nisab, nisab_date = None, None
        if text:
            nisab = check_places(to_decimal(text, "nisab"), 2, "nisab")
            if nisab <= 0:
                raise ValidationError("Type a nisab above zero, or leave it empty.", "typed_nisab")
            nisab_date = old.typed_nisab_date if old.typed_nisab == nisab and old.typed_nisab_date else fmt_date(today())
        after = {"zakat_day": day or None, "typed_nisab": str(nisab) if nisab else None, "typed_nisab_date": nisab_date,
                 "count_worn_gold": bool(count_worn_gold), "deduct_debts_due": bool(deduct_debts_due)}
        before = {"zakat_day": old.zakat_day, "typed_nisab": str(old.typed_nisab) if old.typed_nisab else None,
                  "typed_nisab_date": old.typed_nisab_date, "count_worn_gold": old.count_worn_gold,
                  "deduct_debts_due": old.deduct_debts_due}
        with self.db.transaction():
            self.db.execute(
                "UPDATE zakat_settings SET zakat_day=?,typed_nisab_e6=?,typed_nisab_date=?,count_worn_gold=?,"
                "deduct_debts_due=?,updated_at=? WHERE id=1",
                (day or None, to_e6(nisab) if nisab else None, nisab_date, int(bool(count_worn_gold)),
                 int(bool(deduct_debts_due)), now_iso()))
            self.audit.record("zakat_settings", 1, "edit", "Changed zakat settings", before, after)

    # ------------------------------------------------------------- the nisab
    def gold_price_24k(self, day: str) -> tuple[Decimal, str] | None:
        """The price of a gram of 24K gold in the profile currency on or before the day, with its date: the
        24K reference price, else the newest price of another gold reference divided by its purity."""
        best: tuple[tuple[str, int], Decimal, str] | None = None
        for asset in self.assets.list_assets():
            if asset.exposure.value != "GOLD" or not asset.purity or not asset.code.startswith(("REF:GLD-", "GLD:")):
                continue
            valuation = self.reporting.value_of(asset.id, ONE, day)
            if valuation.value is None or not valuation.price_date:
                continue
            rank = (valuation.price_date, 1 if asset.purity == ONE else 0)  # on the same day the 24K price itself wins
            if best is None or rank > best[0]:
                best = (rank, valuation.value / asset.purity, valuation.price_date)
        return None if best is None else (best[1], best[2])

    def nisab(self, day: str, settings: ZakatSettings) -> tuple[Decimal | None, str, str | None]:
        """(amount, source, date): 85 g of 24K gold at the price of the day, else the nisab the user typed."""
        found = self.gold_price_24k(day)
        if found:
            return (NISAB_GRAMS * found[0]).quantize(CENT, ROUND_HALF_UP), "gold", found[1]
        if settings.typed_nisab:
            return settings.typed_nisab, "typed", settings.typed_nisab_date
        return None, "", None

    # ---------------------------------------------------------- the estimate
    def assess(self, day: date | str | None = None) -> Assessment:
        """Your zakat on a day: the lines, Zakatable wealth, Nisab, Zakat due, Paid this zakat year, Still to pay."""
        on = parse_date(day) if isinstance(day, str) else (day or today())
        text = fmt_date(on)
        settings = self.settings()
        position = self.position.at(on)
        worn_assets = self.physical_items.worn_asset_ids()
        shares = savings_gold = worn_gold = ZERO
        for group in position.classes:
            root = group.code.split(".")[0]
            for item in group.items:
                value = item.value or ZERO
                if root in ("STOCK", "FUND"):
                    shares += value
                elif root == "GOLD":
                    if item.asset_id in worn_assets:
                        worn_gold += value
                    else:
                        savings_gold += value
        lines = [
            ZakatLine("cash", label("cash_you_own"), position.cash_you_own),
            ZakatLine("deposits", label("deposits"), position.deposits),
            ZakatLine("shares", label("shares_and_funds"), shares),
            ZakatLine("gold", label("gold_held_as_savings"), savings_gold),
            # Gam'eya (once claude/gameya is on main): one more line each, from the two Position figures
            #   ZakatLine("gameya_paid", "Gam'eya paid in", position.<Gam'eya paid in>)
            #   ZakatLine("gameya_owed", "Gam'eya still to pay", position.<Gam'eya still to pay>, settings.deduct_debts_due, minus=True)
        ]
        if worn_gold or settings.count_worn_gold:
            lines.append(ZakatLine("worn", label("gold_you_wear"), worn_gold, settings.count_worn_gold))
        lines.append(ZakatLine("debts", label("debts_due_now"), position.bills_due, settings.deduct_debts_due, minus=True))
        wealth = max(ZERO, sum((line.signed for line in lines), ZERO))

        nisab, source, nisab_date = self.nisab(text, settings)
        reason = ""
        if position.unvalued:
            reason = "A price is missing, so Lightning cannot estimate your zakat yet."
        elif nisab is None:
            reason = "There is no gold price yet. Type the nisab behind the gear, or add a gold price."
        due = None
        if not reason:
            due = (wealth * ZAKAT_RATE).quantize(CENT, ROUND_HALF_UP) if wealth >= nisab else ZERO

        days = zakat_days(settings.zakat_day, on)
        paid = still = None
        if days:
            paid = self.paid_between(days[0] + timedelta(days=1), days[1])
            still = None if due is None else max(ZERO, due - paid)
        return Assessment(text, settings, fmt_date(days[1]) if days else None, fmt_date(days[0]) if days else None,
                          tuple(lines), wealth, nisab, source, nisab_date, due, paid, still, reason)

    def paid_between(self, start: date, end: date) -> Decimal:
        """Spending in the Zakat category from the start to the end, both days included."""
        category = self.categories.get_by_code(ZAKAT_CATEGORY)
        return self.reporting.money_out_by_category(start, end).get(category.id, ZERO)

    def forecast(self, day: date | str | None = None) -> ZakatForecast | None:
        """Cash planning's line: the next zakat day and what is still to pay then, at today's figures.
        Nothing until a zakat day is set, and nothing while the estimate cannot be made."""
        found = self.assess(day)
        if found.zakat_day is None or found.still_to_pay is None:
            return None
        return ZakatForecast(found.zakat_day, found.still_to_pay)
