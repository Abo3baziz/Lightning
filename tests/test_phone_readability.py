"""Computed phone layout regressions from the sample profile, at the narrow supported widths."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
CHROMIUM = Path("/opt/pw-browsers/chromium")
if not CHROMIUM.exists():
    CHROMIUM = Path(shutil.which("chromium") or str(CHROMIUM))


@pytest.fixture(scope="module")
def phone_page(tmp_path_factory):
    if not CHROMIUM.exists():
        pytest.skip("Chromium is not installed")
    from playwright.sync_api import sync_playwright
    from lightning.runtime.app import profile_app
    from lightning.runtime.devices import Devices
    from lightning.runtime.http import Host

    root = tmp_path_factory.mktemp("phone-readability")
    host = Host(lambda c: profile_app(c, root / "docs", devices=Devices(root / "app", port=0), phone=True)).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=str(CHROMIUM))
            page = browser.new_page(viewport={"width": 360, "height": 800}, is_mobile=True, has_touch=True)
            page.goto(host.launch_url)
            page.goto(host.origin + "/profiles/new")
            page.fill("input[name=name]", "Phone audit")
            page.fill("input[name=password]", "a dummy phone password")
            page.fill("input[name=confirm]", "a dummy phone password")
            page.fill("input[name=answer]", "Dummy")
            if page.locator("select[name=question]").count():
                page.select_option("select[name=question]", index=1)
            elif page.locator("input[name=question]").count():
                page.fill("input[name=question]", "Dummy question?")
            page.click("button[type=submit]")
            recovery = re.search(r"\d{4}-\d{4}-\d{4}", page.content()).group(0)
            if page.locator("form[action='/profiles/confirm'] input[name=recovery][type=text]").count():
                page.fill("input[name=recovery]", recovery)
            page.click("form[action='/profiles/confirm'] button[type=submit]")
            page.goto(host.origin + "/")
            page.evaluate("""async () => {
              const token = document.querySelector('meta[name=lightning-session]').content;
              await fetch('/demo', {method: 'POST', body: new URLSearchParams({__session: token})});
            }""")
            yield page, host.origin
            browser.close()
    finally:
        host.stop()


@pytest.mark.parametrize("width", [320, 360])
def test_phone_content_fits_and_controls_remain_readable(phone_page, width):
    page, origin = phone_page
    page.set_viewport_size({"width": width, "height": 800})

    page.goto(origin + "/counterparties")
    page.locator(".alias-details summary").first.click()
    save = page.locator(".alias-submit").first
    assert save.is_visible()
    assert save.bounding_box()["height"] >= 48
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

    page.goto(origin + "/birdview/expenses")
    chart = page.locator(".cluster-bars").first
    assert chart.count()
    assert chart.evaluate("el => parseFloat(getComputedStyle(el).height)") <= 104.5
    amount_label = page.locator(".cluster-col small, .cluster-col b").first
    assert amount_label.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") >= 12
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator(".chart-table summary").first.click()
    cell = page.locator(".chart-table table td[data-label]").first
    assert cell.count()
    assert cell.evaluate("el => getComputedStyle(el, '::before').content !== 'none'")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
