"""Crawl every page of a running Lightning (GET links only) and report what is broken.

    python -m lightning --demo --no-browser     # port 8766
    python tools/bug_crawl.py [http://127.0.0.1:8766]

Reports: non-200 pages, pages without a title, broken text (None, nan, undefined, a template tag, a long decimal),
and sideways overflow is left to a browser. Exit status 1 when anything is found. It never posts a form.
"""
from __future__ import annotations

import collections
import html
import re
import sys
import urllib.error
import urllib.request

SKIP = re.compile(r"/(delete|logout|export|download|restore|void)\b|\.(css|js|png|svg|ico|csv|json|woff2?)(\?|$)")
BAD_TEXT = re.compile(r"\b(None|nan|NaN|undefined|Traceback|Infinity)\b|\{\{|\{%|Decimal\(|\d\.\d{3,}\s*(EGP|%)")


def text_of(body: str) -> str:
    body = re.sub(r"<(script|style|svg)[\s\S]*?</\1>", "", body)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)))


def crawl(base: str, limit: int = 600) -> list[str]:
    seen, queue, found = set(), collections.deque(["/"]), []
    while queue and len(seen) < limit:
        path = queue.popleft()
        if path in seen:
            continue
        seen.add(path)
        try:
            with urllib.request.urlopen(base + path, timeout=30) as reply:
                code, body = reply.status, reply.read().decode("utf8", "replace")
        except urllib.error.HTTPError as error:
            code, body = error.code, ""
        except OSError as error:
            found.append(f"unreachable {path}: {error}")
            continue
        if code != 200:
            found.append(f"{code} {path}")
            continue
        if "<html" in body[:400].lower() and not re.search(r"<title>[^<]+</title>", body):
            found.append(f"no title {path}")
        page = text_of(body)
        for match in BAD_TEXT.finditer(page):
            found.append(f"bad text {path}: ...{page[max(0, match.start() - 30):match.end() + 20]}...")
            break
        for href in re.findall(r'href="([^"#]*)"', body):
            href = html.unescape(href)
            if href.startswith("/") and not href.startswith("//") and not SKIP.search(href) and href not in seen:
                queue.append(href)
    print(f"{len(seen)} pages crawled")
    return found


if __name__ == "__main__":
    problems = crawl((sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766").rstrip("/"))
    print("\n".join(problems) or "nothing found")
    sys.exit(1 if problems else 0)
