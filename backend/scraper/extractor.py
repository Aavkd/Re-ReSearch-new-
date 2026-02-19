"""Content extraction: turns a :class:`RawPage` into a :class:`CleanPage`."""

from __future__ import annotations

import re
from typing import List

import trafilatura

from backend.scraper.models import CleanPage, RawPage


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_title(html: str) -> str:
    """Return the text content of the first ``<title>`` tag, or empty string."""
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_links(html: str) -> List[str]:
    """Return a deduplicated list of href values from ``<a>`` tags.

    Fragment-only links (``#anchor``) and empty hrefs are excluded.
    """
    pattern = re.compile(r'<a[^>]+href=["\']([^"\'#][^"\']*)["\']', re.IGNORECASE)
    seen: set[str] = set()
    links: List[str] = []
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        if href and href not in seen:
            seen.add(href)
            links.append(href)
    return links


def _bs4_fallback(html: str) -> str:
    """Extract readable text using BeautifulSoup ``<main>``/``<article>`` heuristics.

    Imported lazily so the rest of the module can be imported without bs4 if
    trafilatura always succeeds in tests.
    """
    from bs4 import BeautifulSoup  # noqa: PLC0415

    soup = BeautifulSoup(html, "html.parser")
    # Strip non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # Prefer structural content containers
    container = soup.find("main") or soup.find("article") or soup.body
    if container is None:
        return soup.get_text(separator=" ", strip=True)
    return container.get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_content(raw: RawPage) -> CleanPage:
    """Extract clean, readable text from *raw*.

    Tries ``trafilatura`` first for best-in-class readability.  Falls back to
    a BeautifulSoup heuristic when trafilatura returns ``None`` or an empty
    string (e.g., highly dynamic or minimal pages).
    """
    text: str | None = trafilatura.extract(
        raw.html,
        include_links=False,
        include_images=False,
        include_tables=True,
        no_fallback=False,
        url=raw.url,
    )

    if not text:
        text = _bs4_fallback(raw.html)

    title = _extract_title(raw.html)
    links = _extract_links(raw.html)

    return CleanPage(
        url=raw.url,
        title=title,
        text=text or "",
        links=links,
    )
