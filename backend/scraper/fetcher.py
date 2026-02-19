"""HTTP fetcher with optional Playwright fallback for JS-rendered pages."""

from __future__ import annotations

import re
import time

import httpx

from backend.config import settings
from backend.scraper.models import RawPage

# ---------------------------------------------------------------------------
# SPA / JS-rendered page detection heuristics
# ---------------------------------------------------------------------------
_SPA_PATTERNS = [
    re.compile(r'<div[^>]+id=["\'](?:root|app)["\']', re.IGNORECASE),
    re.compile(r"window\.__NEXT_DATA__", re.IGNORECASE),
    re.compile(r"ng-version=", re.IGNORECASE),
    re.compile(r"data-reactroot", re.IGNORECASE),
]

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ReSearch-Bot/1.0; +https://github.com/research-bot)"
    )
}


def _is_spa(html: str) -> bool:
    """Return ``True`` if *html* looks like a JavaScript SPA that needs rendering."""
    for pattern in _SPA_PATTERNS:
        if pattern.search(html):
            return True
    # Heuristic: very little visible text relative to total HTML size.
    # Strip <script> and <style> blocks first so their source code doesn't
    # count as visible text, then strip remaining tags.
    no_scripts = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.IGNORECASE | re.DOTALL)
    stripped = re.sub(r"<[^>]+>", "", no_scripts).strip()
    if len(html) > 2000 and len(stripped) < 200:
        return True
    return False


def _fetch_with_playwright(url: str) -> RawPage:
    """Render *url* with a headless Chromium browser and return its HTML.

    Playwright is imported lazily so tests that don't exercise the SPA path
    don't need a browser installed.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(
            url,
            timeout=int(settings.request_timeout * 1000),
            wait_until="networkidle",
        )
        html = page.content()
        browser.close()

    return RawPage(url=url, html=html, status_code=200)


def fetch_url(url: str) -> RawPage:
    """Fetch *url* and return a :class:`RawPage`.

    Uses ``httpx`` for standard pages.  Automatically falls back to a headless
    Playwright browser when a JavaScript SPA fingerprint is detected in the
    initial response.

    Raises:
        httpx.HTTPStatusError: If the server returns a 4xx/5xx status code.
    """
    time.sleep(settings.rate_limit_delay)

    with httpx.Client(
        headers=_DEFAULT_HEADERS,
        timeout=settings.request_timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
        status_code = response.status_code

    raw = RawPage(url=url, html=html, status_code=status_code)

    if _is_spa(raw.html):
        raw = _fetch_with_playwright(url)

    return raw
