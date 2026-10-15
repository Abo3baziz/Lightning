"""Download each built-in institution's logo once, for bundling (never fetched while the app runs).

Run from a PC with internet access:  python tools/fetch_institution_logos.py [--only cib,nbe] [--force]

For every row of lightning/accounts/institutions.csv with a website and no logo, it asks the site for its
apple-touch-icon (else the favicon), shrinks it to at most 64 px and 8 KB, saves it as
lightning/ui/static/institutions/<code>.png and writes the file name into the CSV's `logo` column.
A row with no usable icon keeps an empty logo and shows a monogram tile. Needs Pillow (`pip install pillow`).
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "lightning" / "accounts" / "institutions.csv"
OUT_DIR = ROOT / "lightning" / "ui" / "static" / "institutions"
MAX_BYTES = 8 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0 (Lightning logo fetch)"}


def _get(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15) as response:
            return response.read(2_000_000)
    except Exception:
        return None


def _icon_urls(site: str) -> list[str]:
    base = f"https://{site}"
    urls = []
    page = _get(base)
    if page:
        html = page.decode("utf-8", "replace")
        for tag in re.findall(r"<link[^>]+>", html, flags=re.I):
            if re.search(r'rel=["\'][^"\']*(apple-touch-icon|icon)', tag, flags=re.I):
                href = re.search(r'href=["\']([^"\']+)', tag, flags=re.I)
                if href:
                    h = href.group(1)
                    urls.append(h if h.startswith("http") else f"{base}/{h.lstrip('/')}" if not h.startswith("//") else f"https:{h}")
    return urls + [f"{base}/apple-touch-icon.png", f"{base}/favicon.ico"]


def _shrink(data: bytes) -> bytes | None:
    from PIL import Image
    try:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None
    image.thumbnail((64, 64))
    for colours in (256, 64, 16):
        out = io.BytesIO()
        image.quantize(colours, method=Image.Quantize.FASTOCTREE).save(out, "PNG", optimize=True)
        if out.tell() <= MAX_BYTES:
            return out.getvalue()
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="", help="comma-separated institution codes")
    parser.add_argument("--force", action="store_true", help="fetch again even when a logo is set")
    args = parser.parse_args(argv)
    only = {code for code in args.only.split(",") if code}
    rows = list(csv.DictReader(CSV_FILE.open(encoding="utf-8", newline="")))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    got = 0
    for row in rows:
        if (only and row["code"] not in only) or not row["website"] or (row["logo"] and not args.force):
            continue
        for url in _icon_urls(row["website"]):
            data = _get(url)
            small = _shrink(data) if data else None
            if small:
                (OUT_DIR / f"{row['code']}.png").write_bytes(small)
                row["logo"] = f"{row['code']}.png"
                got += 1
                print(f"{row['code']}: {url}")
                break
        else:
            print(f"{row['code']}: no logo (monogram)")
    with CSV_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{got} logos saved to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
