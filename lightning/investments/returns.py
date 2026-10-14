"""Return shown to a person: actual gain under a year, dated annual return after it."""
from dataclasses import dataclass
from decimal import Decimal

from lightning.core.dates import parse_date
from lightning.core.money import ZERO


@dataclass(frozen=True)
class DisplayReturn:
    percent: Decimal | None
    annualized: bool
    days_held: int | None


def display_return(flows: list[tuple[str, Decimal]], on: str, annual_rate: Decimal | None,
                   valued: bool = True) -> DisplayReturn:
    """Flows include purchases, sales, income and terminal value, all in the profile currency.

    Plain return divides net gain by all money invested, so partial sales and income count
    without treating the cost of the remaining units as the original investment.
    The XIRR solver stays unchanged; this is only the display policy.
    """
    purchases = [(day, -amount) for day, amount in flows if amount < ZERO]
    if not purchases:
        return DisplayReturn(None, False, None)
    days = (parse_date(on) - parse_date(min(day for day, _ in purchases))).days
    annualized = days >= 365
    invested = sum((amount for _, amount in purchases), ZERO)
    percent = (annual_rate * 100 if annual_rate is not None else None) if annualized else (
        sum((amount for _, amount in flows), ZERO) / invested * 100)
    return DisplayReturn(percent if valued else None, annualized, days)
