"""Rebuild lightning/assets/us_instruments.csv, the picker's list of US stocks and ETFs, from the TradingView
`america` screener the collector already reads (lightning/market/sources/tradingview.py).

    python -m tools.market.us_catalogue [--stocks 300] [--etfs 60] [--out lightning/assets/us_instruments.csv]

The file in the repository was first compiled by hand (source "compiled list"); run this from a machine that can
reach TradingView to replace it with the screener's largest stocks (by market value) and ETFs (by assets).
A ticker that is also an EGX ticker is left out, because an asset's code is STK:<ticker>.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

from lightning.market.http import Polite
from lightning.market.sources import tradingview

ROOT = Path(__file__).resolve().parents[2] / "lightning" / "assets"
HEAD = ["ticker", "name", "kind", "class_code", "source", "source_url", "catalogue_date", "mic", "currency"]
SOURCE = "TradingView america scanner"


def fund_class(name: str, known: str = "") -> str:
    """The picker's class for an ETF: the one already in the file, else read from its name."""
    if known:
        return known
    text = name.casefold()
    if "gold" in text:
        return "FUND.GOLD"
    if re.search(r"\b(bond|treasury|aggregate|tips|income securities|municipal|credit|t-bill)\b", text):
        return "FUND.FIXED_INCOME"
    if re.search(r"\b(silver|oil|commodity|bitcoin|ether|crypto|currency|volatility)\b", text):
        return "FUND.OTHER"
    return "FUND.EQUITY"


def rows_from(parts, egx_tickers: set[str], known: dict[str, str], day: str) -> list[list[str]]:
    """CSV rows from parsed screener answers (SourceResult list), stocks first, one row per ticker."""
    seen, rows = set(), []
    for part in parts:
        for item in part.instruments:
            ticker = item.ticker.upper()
            if ticker in seen or ticker in egx_tickers or item.currency != "USD":
                continue
            seen.add(ticker)
            fund = item.category.startswith("FUND")
            rows.append([ticker, item.name, "ETFs" if fund else "Stocks",
                         fund_class(item.name, known.get(ticker, "")) if fund else "STOCK",
                         SOURCE, tradingview.SCAN.format(screener="america"), day, item.mic, "USD"])
    return sorted(rows, key=lambda row: (row[2] != "Stocks", row[1].casefold()))


def rebuild(session, out: Path, stocks: int = 300, etfs: int = 60, day: str | None = None) -> int:
    day = day or date.today().isoformat()
    board = replace(tradingview.BOARDS["us"][0], stocks=stocks, etfs=etfs)
    parts = [tradingview.parse(session.post_json(tradingview.SCAN.format(screener=board.screener),
                                                 tradingview.query(board, kind)), board, day, "tradingview-us")
             for kind in ("stocks", "etfs")]
    with (ROOT / "egx_instruments.csv").open(encoding="utf-8-sig", newline="") as source:
        egx = {row["ticker"].upper() for row in csv.DictReader(source)}
    known = {}
    if out.exists():
        with out.open(encoding="utf-8-sig", newline="") as source:
            known = {row["ticker"]: row["class_code"] for row in csv.DictReader(source) if row["kind"] == "ETFs"}
    rows = rows_from(parts, egx, known, day)
    with out.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(HEAD)
        writer.writerows(rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--stocks", type=int, default=300)
    parser.add_argument("--etfs", type=int, default=60)
    parser.add_argument("--out", type=Path, default=ROOT / "us_instruments.csv")
    args = parser.parse_args(argv)
    count = rebuild(Polite(), args.out, args.stocks, args.etfs)
    print(f"Wrote {count} instruments to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
