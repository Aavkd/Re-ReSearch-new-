"""Unit tests for backend.agent.search_providers.

All network calls are mocked via ``unittest.mock``.  No real HTTP connections
are made; the tests validate provider-level parsing, retry logic, and
chain-level failover behaviour.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()  # no-op by default
    return resp


# ===========================================================================
# SearXNGProvider
# ===========================================================================

class TestSearXNGProvider:
    def test_parses_json_results(self):
        from backend.agent.search_providers import SearXNGProvider

        json_data = {
            "results": [
                {"url": "https://example.com/a"},
                {"url": "https://example.com/b"},
                {"href": "https://example.com/c"},   # alternate key
            ]
        }
        mock_resp = _mock_httpx_response(json_data)

        with patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_resp
            mock_client_cls.return_value = ctx

            provider = SearXNGProvider()
            result = provider.search("test query", max_results=5)

        assert "https://example.com/a" in result
        assert "https://example.com/b" in result

    def test_respects_max_results(self):
        from backend.agent.search_providers import SearXNGProvider

        json_data = {
            "results": [{"url": f"https://example.com/{i}"} for i in range(10)]
        }
        mock_resp = _mock_httpx_response(json_data)

        with patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_resp
            mock_client_cls.return_value = ctx

            provider = SearXNGProvider()
            result = provider.search("test query", max_results=3)

        assert len(result) == 3

    def test_returns_empty_on_http_error(self):
        from backend.agent.search_providers import SearXNGProvider
        import httpx

        with patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value = ctx

            provider = SearXNGProvider()
            result = provider.search("test query")

        assert result == []

    def test_returns_empty_on_json_parse_error(self):
        from backend.agent.search_providers import SearXNGProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("invalid JSON")

        with patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_resp
            mock_client_cls.return_value = ctx

            provider = SearXNGProvider()
            result = provider.search("test query")

        assert result == []

    def test_deduplicates_urls(self):
        from backend.agent.search_providers import SearXNGProvider

        json_data = {
            "results": [
                {"url": "https://dup.com"},
                {"url": "https://dup.com"},
                {"url": "https://unique.com"},
            ]
        }
        mock_resp = _mock_httpx_response(json_data)

        with patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_resp
            mock_client_cls.return_value = ctx

            provider = SearXNGProvider()
            result = provider.search("test", max_results=10)

        assert result.count("https://dup.com") == 1


# ===========================================================================
# DuckDuckGoProvider
# ===========================================================================

class TestDuckDuckGoProvider:
    def test_returns_urls_on_success(self):
        from backend.agent.search_providers import DuckDuckGoProvider
        from duckduckgo_search import DDGS

        fake_results = [{"href": "https://a.com"}, {"href": "https://b.com"}]
        with patch("backend.agent.search_providers.DDGS") as mock_ddgs_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(return_value=fake_results)
            mock_ddgs_cls.return_value = ctx

            provider = DuckDuckGoProvider()
            result = provider.search("query", max_results=5)

        assert result == ["https://a.com", "https://b.com"]

    def test_retries_on_ratelimit_then_succeeds(self):
        from backend.agent.search_providers import DuckDuckGoProvider
        from duckduckgo_search.exceptions import RatelimitException

        fake_results = [{"href": "https://ok.com"}]

        call_count = 0
        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on first attempt, succeed on second.
            if call_count == 1:
                raise RatelimitException("rate limited")
            return fake_results

        with patch("backend.agent.search_providers.DDGS") as mock_ddgs_cls, \
             patch("backend.agent.search_providers.time.sleep"):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(side_effect=_side_effect)
            mock_ddgs_cls.return_value = ctx

            provider = DuckDuckGoProvider()
            result = provider.search("query")

        assert result == ["https://ok.com"]
        assert call_count == 2

    def test_returns_empty_after_exhausting_retries(self):
        from backend.agent.search_providers import DuckDuckGoProvider
        from duckduckgo_search.exceptions import RatelimitException

        with patch("backend.agent.search_providers.DDGS") as mock_ddgs_cls, \
             patch("backend.agent.search_providers.time.sleep"), \
             patch("backend.agent.search_providers.settings") as mock_settings:
            mock_settings.search_retry_max = 2
            mock_settings.search_retry_base_delay = 0.0

            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(side_effect=RatelimitException("always rate limited"))
            mock_ddgs_cls.return_value = ctx

            provider = DuckDuckGoProvider()
            result = provider.search("query")

        assert result == []

    def test_returns_empty_on_ratelimit_in_exception_message(self):
        """Older duckduckgo_search versions surface rate-limits as generic RuntimeError."""
        from backend.agent.search_providers import DuckDuckGoProvider

        with patch("backend.agent.search_providers.DDGS") as mock_ddgs_cls, \
             patch("backend.agent.search_providers.time.sleep"), \
             patch("backend.agent.search_providers.settings") as mock_settings:
            mock_settings.search_retry_max = 1
            mock_settings.search_retry_base_delay = 0.0

            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(side_effect=RuntimeError("https://html.duckduckgo.com/html 202 Ratelimit"))
            mock_ddgs_cls.return_value = ctx

            provider = DuckDuckGoProvider()
            result = provider.search("query")

        assert result == []


# ===========================================================================
# BraveSearchProvider
# ===========================================================================

class TestBraveSearchProvider:
    def test_skipped_without_api_key(self):
        from backend.agent.search_providers import BraveSearchProvider

        with patch("backend.agent.search_providers.settings") as mock_settings:
            mock_settings.brave_api_key = ""
            provider = BraveSearchProvider()
            result = provider.search("test")

        assert result == []

    def test_parses_response_correctly(self):
        from backend.agent.search_providers import BraveSearchProvider

        json_data = {
            "web": {
                "results": [
                    {"url": "https://brave-result.com/1"},
                    {"url": "https://brave-result.com/2"},
                ]
            }
        }
        mock_resp = _mock_httpx_response(json_data)

        with patch("backend.agent.search_providers.settings") as mock_settings, \
             patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            mock_settings.brave_api_key = "test-key-abc"
            mock_settings.search_provider_timeout = 10.0

            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.return_value = mock_resp
            mock_client_cls.return_value = ctx

            provider = BraveSearchProvider()
            result = provider.search("test query", max_results=5)

        assert result == ["https://brave-result.com/1", "https://brave-result.com/2"]

    def test_returns_empty_on_network_error(self):
        from backend.agent.search_providers import BraveSearchProvider
        import httpx

        with patch("backend.agent.search_providers.settings") as mock_settings, \
             patch("backend.agent.search_providers.httpx.Client") as mock_client_cls:
            mock_settings.brave_api_key = "test-key"
            mock_settings.search_provider_timeout = 10.0

            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.get.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value = ctx

            provider = BraveSearchProvider()
            result = provider.search("test query")

        assert result == []


# ===========================================================================
# SearchProviderChain
# ===========================================================================

class TestSearchProviderChain:
    def _make_provider(self, name: str, returns: list[str]) -> MagicMock:
        p = MagicMock()
        p.name = name
        p.search.return_value = returns
        return p

    def test_returns_first_successful_result(self):
        from backend.agent.search_providers import SearchProviderChain

        p1 = self._make_provider("P1", ["https://p1.com"])
        p2 = self._make_provider("P2", ["https://p2.com"])
        chain = SearchProviderChain([p1, p2])

        result = chain.search("query")

        assert result == ["https://p1.com"]
        p2.search.assert_not_called()

    def test_falls_through_to_second_on_empty_first(self):
        from backend.agent.search_providers import SearchProviderChain

        p1 = self._make_provider("P1", [])
        p2 = self._make_provider("P2", ["https://p2.com"])
        chain = SearchProviderChain([p1, p2])

        result = chain.search("query")

        assert result == ["https://p2.com"]
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_returns_empty_when_all_fail(self):
        from backend.agent.search_providers import SearchProviderChain

        p1 = self._make_provider("P1", [])
        p2 = self._make_provider("P2", [])
        chain = SearchProviderChain([p1, p2])

        result = chain.search("query")

        assert result == []

    def test_passes_max_results_to_provider(self):
        from backend.agent.search_providers import SearchProviderChain

        p1 = self._make_provider("P1", ["https://result.com"])
        chain = SearchProviderChain([p1])

        chain.search("query", max_results=7)

        p1.search.assert_called_once_with("query", max_results=7)

    def test_empty_chain_returns_empty(self):
        from backend.agent.search_providers import SearchProviderChain

        chain = SearchProviderChain([])
        result = chain.search("query")

        assert result == []


# ===========================================================================
# build_default_chain
# ===========================================================================

class TestBuildDefaultChain:
    def test_includes_searxng_and_ddg(self):
        from backend.agent.search_providers import (
            BraveSearchProvider,
            DuckDuckGoProvider,
            SearchProviderChain,
            SearXNGProvider,
            build_default_chain,
        )

        with patch("backend.agent.search_providers.settings") as mock_settings:
            mock_settings.brave_api_key = ""
            mock_settings.searxng_base_url = "https://searx.be"
            chain = build_default_chain()

        assert isinstance(chain, SearchProviderChain)
        names = [p.name for p in chain._providers]
        assert "SearXNG" in names
        assert "DuckDuckGo" in names
        assert "Brave" not in names  # no key configured

    def test_includes_brave_when_key_configured(self):
        from backend.agent.search_providers import BraveSearchProvider, build_default_chain

        with patch("backend.agent.search_providers.settings") as mock_settings:
            mock_settings.brave_api_key = "my-brave-key"
            mock_settings.searxng_base_url = "https://searx.be"
            chain = build_default_chain()

        names = [p.name for p in chain._providers]
        assert "Brave" in names


# ===========================================================================
# web_search integration (tools.py)
# ===========================================================================

class TestWebSearchFunction:
    def test_delegates_to_chain(self):
        """web_search() signature unchanged; internally uses the chain."""
        import backend.agent.tools as tools_module

        # Reset singleton so the mock is used.
        tools_module._search_chain = None

        mock_chain = MagicMock()
        mock_chain.search.return_value = ["https://via-chain.com"]

        with patch("backend.agent.tools.build_default_chain", return_value=mock_chain):
            tools_module._search_chain = None  # force re-init
            from backend.agent.tools import web_search
            tools_module._search_chain = None  # ensure fresh chain

            with patch("backend.agent.tools._get_search_chain", return_value=mock_chain):
                result = web_search("test query", max_results=3)

        mock_chain.search.assert_called_once_with("test query", max_results=3)
        assert result == ["https://via-chain.com"]
