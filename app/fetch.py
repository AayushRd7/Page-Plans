"""HTTP fetch with a browser fallback.

Stores like everythingfor420.com 429 plain curl; a real Chromium via
playwright gets through. JSON APIs usually answer plain requests fine,
so try requests first and escalate only on failure.
"""
import json as _json

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def fetch_text(url: str, timeout: int = 30) -> tuple[int, str, str]:
    """-> (status, final_url, body). Raises on hard network failure."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout,
                         allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 200:
            return r.status_code, r.url, r.text
        status, final = r.status_code, r.url
    except requests.RequestException:
        status, final = 0, url
    status, final, body = _playwright_fetch(url, timeout)
    return status, final, body


def fetch_json(url: str, timeout: int = 30):
    status, final, body = fetch_text(url, timeout)
    if status != 200:
        return status, final, None
    try:
        return status, final, _json.loads(body)
    except ValueError:
        return status, final, None


def _playwright_fetch(url: str, timeout: int) -> tuple[int, str, str]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(user_agent=UA)
        try:
            resp = page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            # trigger lazy-loaded product grids: real window scrolls in steps
            last = 0
            for _ in range(10):
                page.evaluate("window.scrollBy(0, 2500)")
                page.wait_for_timeout(800)
                height = page.evaluate("document.body.scrollHeight")
                if height == last:
                    break
                last = height
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            status = resp.status if resp else 0
            return status, page.url, page.content()
        finally:
            browser.close()
