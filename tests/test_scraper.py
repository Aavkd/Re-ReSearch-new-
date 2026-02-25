"""Tests for Phase 2 — web scraper (fetch + content extraction).

Mocking strategy:
- ``respx`` patches ``httpx`` at the transport layer so no real network calls
  are made during ``fetch_url`` tests.
- ``time.sleep`` is patched to avoid real delays from ``settings.rate_limit_delay``.
- ``trafilatura.extract`` is patched in the BS4-fallback test to simulate the
  case where trafilatura returns nothing.
- Playwright is *not* exercised in the test suite (requires a browser install);
  the SPA-fallback path is covered by a unit test against ``_is_spa`` directly.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import respx
import httpx

from backend.scraper.models import RawPage, CleanPage
from backend.scraper.fetcher import _is_spa, fetch_url
from backend.scraper.extractor import (
    _extract_title,
    _extract_links,
    _bs4_fallback,
    extract_content,
)


# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

_SIMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
  <main>
    <p>This is the main content of the test page with enough text for extraction.</p>
    <p>It discusses topics such as renewable energy and battery technology.</p>
    <a href="https://example.com/page1">Link 1</a>
    <a href="https://example.com/page2">Link 2</a>
    <a href="#fragment">Fragment (excluded)</a>
  </main>
</body>
</html>
"""

_SPA_HTML = """\
<!DOCTYPE html>
<html>
<head><title>React App</title></head>
<body>
  <div id="root"></div>
  <script src="/bundle.js"></script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# _is_spa unit tests
# ---------------------------------------------------------------------------

class TestIsSpa:
    def test_detects_react_root_div(self) -> None:
        assert _is_spa(_SPA_HTML) is True

    def test_detects_next_data(self) -> None:
        html = "<html><body><script>window.__NEXT_DATA__ = {}</script></body></html>"
        assert _is_spa(html) is True

    def test_detects_angular(self) -> None:
        html = '<html ng-version="12.0.0"><body>content</body></html>'
        assert _is_spa(html) is True

    def test_detects_react_root_attr(self) -> None:
        html = '<html><body><div data-reactroot=""></div></body></html>'
        assert _is_spa(html) is True

    def test_normal_page_not_spa(self) -> None:
        assert _is_spa(_SIMPLE_HTML) is False

    def test_minimal_body_heuristic(self) -> None:
        # Long HTML (>2000 chars) with next-to-no visible text triggers the heuristic
        big_script = "<script>" + "x" * 2500 + "</script>"
        html = f"<html><body>{big_script}<p> </p></body></html>"
        assert _is_spa(html) is True


# ---------------------------------------------------------------------------
# fetch_url tests
# ---------------------------------------------------------------------------

class TestFetchUrl:
    def test_successful_fetch_returns_raw_page(self) -> None:
        """A 200 response is returned as a RawPage."""
        with respx.mock:
            respx.get("https://example.com/article").mock(
                return_value=httpx.Response(200, text=_SIMPLE_HTML)
            )
            raw = fetch_url("https://example.com/article")

        assert isinstance(raw, RawPage)
        assert raw.url == "https://example.com/article"
        assert raw.status_code == 200
        assert "<title>Test Page</title>" in raw.html

    def test_http_error_raises(self) -> None:
        """A 404 response raises ``httpx.HTTPStatusError``."""
        with respx.mock:
            respx.get("https://example.com/missing").mock(
                return_value=httpx.Response(404, text="Not Found")
            )
            with pytest.raises(httpx.HTTPStatusError):
                fetch_url("https://example.com/missing")

    def test_no_rate_limit_sleep_on_fetch(self) -> None:
        """``fetch_url`` must NOT call ``time.sleep``; rate-limiting lives at the
        agent layer (thread-pool size) not in the fetcher."""
        with respx.mock:
            respx.get("https://example.com/").mock(
                return_value=httpx.Response(200, text=_SIMPLE_HTML)
            )
            with patch("time.sleep") as mock_sleep:
                fetch_url("https://example.com/")

        mock_sleep.assert_not_called()

    def test_spa_triggers_playwright_fallback(self) -> None:
        """SPA HTML causes ``_fetch_with_playwright`` to be invoked."""
        playwright_result = RawPage(
            url="https://spa-app.example.com/",
            html=_SIMPLE_HTML,
            status_code=200,
        )
        with respx.mock:
            respx.get("https://spa-app.example.com/").mock(
                return_value=httpx.Response(200, text=_SPA_HTML)
            )
            with patch("backend.scraper.fetcher._fetch_with_playwright",
                       return_value=playwright_result) as mock_pw:
                raw = fetch_url("https://spa-app.example.com/")

        mock_pw.assert_called_once_with("https://spa-app.example.com/")
        assert raw.html == _SIMPLE_HTML


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------

class TestExtractTitle:
    def test_extracts_title(self) -> None:
        assert _extract_title(_SIMPLE_HTML) == "Test Page"

    def test_missing_title_returns_empty(self) -> None:
        assert _extract_title("<html><body></body></html>") == ""

    def test_title_with_attributes(self) -> None:
        html = '<html><head><title lang="en">My Title</title></head></html>'
        assert _extract_title(html) == "My Title"


class TestExtractLinks:
    def test_extracts_absolute_links(self) -> None:
        links = _extract_links(_SIMPLE_HTML)
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_excludes_fragment_links(self) -> None:
        links = _extract_links(_SIMPLE_HTML)
        assert not any(lnk.startswith("#") for lnk in links)

    def test_deduplicates_links(self) -> None:
        html = (
            '<html><body>'
            '<a href="https://a.com">1</a>'
            '<a href="https://a.com">2</a>'
            '</body></html>'
        )
        links = _extract_links(html)
        assert links.count("https://a.com") == 1

    def test_no_links_returns_empty(self) -> None:
        assert _extract_links("<html><body>no links</body></html>") == []


class TestBs4Fallback:
    def test_extracts_main_content(self) -> None:
        text = _bs4_fallback(_SIMPLE_HTML)
        assert "main content" in text.lower()

    def test_strips_scripts_and_styles(self) -> None:
        html = """\
<html><body>
  <script>alert('x')</script>
  <style>.a{color:red}</style>
  <main><p>Real content here.</p></main>
</body></html>
"""
        text = _bs4_fallback(html)
        assert "alert" not in text
        assert "color" not in text
        assert "Real content" in text

    def test_falls_back_to_body_when_no_main(self) -> None:
        html = "<html><body><p>Body text.</p></body></html>"
        text = _bs4_fallback(html)
        assert "Body text." in text


class TestExtractContent:
    def test_returns_clean_page(self) -> None:
        raw = RawPage(url="https://example.com/", html=_SIMPLE_HTML, status_code=200)
        clean = extract_content(raw)

        assert isinstance(clean, CleanPage)
        assert clean.url == "https://example.com/"
        assert clean.title == "Test Page"
        assert len(clean.text) > 0
        assert isinstance(clean.links, list)

    def test_trafilatura_fallback_to_bs4(self) -> None:
        """When trafilatura returns None the BS4 fallback provides text."""
        raw = RawPage(url="https://example.com/", html=_SIMPLE_HTML, status_code=200)
        with patch("backend.scraper.extractor.trafilatura.extract", return_value=None):
            clean = extract_content(raw)

        assert "main content" in clean.text.lower()

    def test_empty_html_does_not_raise(self) -> None:
        """Completely empty pages should not raise; text is an empty string."""
        raw = RawPage(url="https://example.com/", html="<html></html>", status_code=200)
        clean = extract_content(raw)
        assert isinstance(clean.text, str)

    def test_links_populated(self) -> None:
        raw = RawPage(url="https://example.com/", html=_SIMPLE_HTML, status_code=200)
        clean = extract_content(raw)
        assert "https://example.com/page1" in clean.links
