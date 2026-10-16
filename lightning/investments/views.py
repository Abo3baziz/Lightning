"""The Investments holdings table grouped five ways, the By currency breakdown and the USD lens.

Every figure here is arithmetic on rows the route already built: a view only regroups the same holdings, so each
view's total is Holdings value. Nothing is stored; the USD lens is a display conversion at one dated rate.
"""
from __future__ import annotations

from decimal import Decimal

from lightning.core.money import ZERO
from lightning.market.iso import venue_name

VIEWS = ("class", "account", "currency", "market", "security")
VIEW_LABELS = {"class": "By class", "account": "By account", "currency": "By currency", "market": "By market",
               "security": "By security"}
SHOWN = 4  # guideline A16: four names, then Other


def parse_view(text: str | None) -> str:
    return text if text in VIEWS else "class"


def make_group(name: str, rows: list[dict], holdings_total: Decimal) -> dict:
    group = {"name": name, "value": ZERO, "cost": ZERO, "gain": ZERO, "invested": ZERO, "rows": rows}
    for r in rows:
        group["value"] += r["value"] or ZERO
        group["cost"] += r["cost"] or ZERO
        group["gain"] += r.get("gain") or ZERO
        group["invested"] += r.get("invested", r["value"] or ZERO)
    rows.sort(key=lambda r: (-(r["value"] or ZERO), (r["h"].asset_name if r["h"] else r["name"]).casefold()))
    group["weight"] = group["value"] / holdings_total * 100 if holdings_total else ZERO
    group["gain_pct"] = group["gain"] / group["invested"] * 100 if group["invested"] else None
    return group


def regroup(view: str, class_groups: list[dict], holdings_total: Decimal, *, accounts: dict, assets: dict,
            base: str, other_label: str = "Other") -> list[dict]:
    """The same rows, grouped by ``view``. ``accounts`` maps id -> Account, ``assets`` maps id -> asset."""
    if view == "class":
        return class_groups
    keyed: dict[str, list[dict]] = {}
    for g in class_groups:
        for r in g["rows"]:
            h = r["h"]
            asset = assets.get(h.asset_id if h else r.get("asset_id"))
            if view == "account":
                account = accounts.get(h.account_id if h else r["account_id"])
                parent = accounts.get(getattr(account, "parent_id", None))  # a pocket rolls up into its broker
                owner = parent or account
                name = owner.name if owner else (h.account_label if h else r["name"])
            elif view == "currency":
                name = (asset.currency if asset is not None else None) or base
            elif view == "market":
                mic = getattr(asset, "mic", None)
                name = venue_name(mic) if mic else g["name"]  # unlisted: its kind (Certificates, Gold, ...)
            else:  # security: one row per asset, the accounts that hold it beneath
                name = h.asset_name if h else r["name"]
            keyed.setdefault(name, []).append(r)
    groups = sorted((make_group(n, rows, holdings_total) for n, rows in keyed.items()),
                    key=lambda g: (-g["value"], g["name"].casefold()))
    if view == "market" and len(groups) > SHOWN + 1:
        tail = [r for g in groups[SHOWN:] for r in g["rows"]]
        groups = groups[:SHOWN] + [make_group(other_label, tail, holdings_total)]
    return groups


def by_currency(holdings: dict[str, Decimal], cash: dict[str, Decimal], base: str, other_label: str = "Other") -> dict:
    """Value per currency (holdings plus brokerage cash), in the profile currency: four, then Other.

    ``holdings`` and ``cash`` map a currency code to its value in the profile currency."""
    totals: dict[str, Decimal] = {}
    for source in (holdings, cash):
        for code, value in source.items():
            totals[code] = totals.get(code, ZERO) + (value or ZERO)
    total = sum(totals.values(), ZERO)
    ordered = sorted(((c, v) for c, v in totals.items() if v), key=lambda i: (-i[1], i[0]))
    shown, rest = ordered[:SHOWN], ordered[SHOWN:]
    if len(rest) == 1:  # one name is not worth an Other
        shown, rest = ordered, []
    rows = [{"label": c, "value": v, "share": v / total * 100 if total else ZERO} for c, v in shown]
    if rest:
        rest_value = sum((v for _, v in rest), ZERO)
        rows.append({"label": other_label, "value": rest_value, "share": rest_value / total * 100 if total else ZERO,
                     "note": ", ".join(c for c, _ in rest)})
    abroad = total - totals.get(base, ZERO)
    return {"rows": rows, "total": total, "abroad": abroad, "abroad_share": abroad / total * 100 if total else ZERO}


def fx_total(rows: list[dict]) -> Decimal:
    """What the exchange rate added to the unrealized gain of foreign holdings (sum of fx_part)."""
    return sum((r["fx_part"] for r in rows if r.get("fx_part") is not None), ZERO)


def in_lens(groups: list[dict], divisor: Decimal) -> list[dict]:
    """The groups with every pound figure divided by ``divisor`` (units, native prices and percentages stay)."""
    out = []
    for g in groups:
        rows = []
        for r in g["rows"]:
            row = dict(r)
            for key in ("cost", "value", "gain", "price_part", "fx_part"):
                if r.get(key) is not None:
                    row[key] = r[key] / divisor
            if not r.get("currency"):  # a pound price per unit; a foreign one stays in its own currency
                for key in ("average_cost", "price"):
                    if r.get(key) is not None:
                        row[key] = r[key] / divisor
            rows.append(row)
        out.append({**g, "rows": rows, "value": g["value"] / divisor, "cost": g["cost"] / divisor,
                    "gain": g["gain"] / divisor})
    return out
