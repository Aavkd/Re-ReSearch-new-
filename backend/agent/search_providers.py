"""Multi-provider web search abstraction with automatic failover.

Provider priority (highest to lowest):
  1. Brave Search — fast REST API, deterministic; requires BRAVE_API_KEY.
  2. SearXNG  — free metasearch, rotates multiple public instances.
  3. DuckDuckGo — free, scraping-based; retried with exponential backoff.

All providers share a common interface: ``search(query, max_results) -> list[str]``.
The ``SearchProviderChain`` tries each provider in order and returns the first
non-empty result set.  If every provider fails the chain returns ``[]``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import httpx
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException, RatelimitException

from backend.config import settings

# ---------------------------------------------------------------------------
# Reliable public SearXNG instances (tried in order on failure)
# ---------------------------------------------------------------------------
_SEARXNG_FALLBACK_INSTANCES = [
    "https://search.bus-hit.me",
    "https://searx.be",
    "https://paulgo.io",
    "https://searx.tiekoetter.com",
]

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _normalise_query(query: str) -> str:
    """Strip surrounding double-quotes added by the LLM planner.

    The planner wraps queries in literal quotes, e.g. ``'"topic"'``.
    These cause some search engines to refuse or return no results.
    """
    q = query.strip()
    if q.startswith('"') and q.endswith('"') and len(q) > 2:
        q = q[1:-1].strip()
    return q


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class SearchProvider(ABC):
    """Abstract base class for a single search provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[str]:
        """Return a list of URLs.  Must return ``[]`` (not raise) on failure."""


# ---------------------------------------------------------------------------
# Brave Search provider (preferred — deterministic, fast REST API)
# ---------------------------------------------------------------------------

class BraveSearchProvider(SearchProvider):
    """Brave Search REST API (free tier: 2 000 queries/month).

    Skipped if ``settings.brave_api_key`` is empty.
    """

    @property
    def name(self) -> str:
        return "Brave"

    def search(self, query: str, max_results: int = 5) -> list[str]:
        api_key = settings.brave_api_key
        if not api_key:
            return []

        query = _normalise_query(query)
        try:
            with httpx.Client(timeout=settings.search_provider_timeout) as client:
                resp = client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": max_results},
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            print(f"[Brave] request failed: {exc}")
            return []

        results = [
            item["url"]
            for item in data.get("web", {}).get("results", [])
            if item.get("url")
        ]
        if results:
            print(f"[Brave] ✓ {len(results)} result(s).")
        return results


# ---------------------------------------------------------------------------
# SearXNG provider
# ---------------------------------------------------------------------------

class SearXNGProvider(SearchProvider):
    """Hit a SearXNG JSON endpoint.

    Tries the configured base URL first (`settings.searxng_base_url`), then
    rotates through ``_SEARXNG_FALLBACK_INSTANCES`` on failure.

    Each instance is queried with a tight ``searxng_instance_timeout`` (default
    5 s) so dead or rate-limited instances fail fast rather than blocking for
    the full ``search_provider_timeout``.
    """

    @property
    def name(self) -> str:
        return "SearXNG"

    def _query_instance(
        self,
        client: httpx.Client,
        base: str,
        query: str,
        max_results: int,
    ) -> list[str]:
        resp = client.get(
            f"{base}/search",
            params={
                "q": query,
                "format": "json",
                "engines": "google,bing,brave,duckduckgo",
            },
            headers={
                "Accept": "application/json, text/javascript, */*",
                "User-Agent": _BROWSER_UA,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results: list[str] = []
        for item in data.get("results", []):
            url = item.get("url") or item.get("href")
            if url and url not in results:
                results.append(url)
            if len(results) >= max_results:
                break
        return results

    def search(self, query: str, max_results: int = 5) -> list[str]:
        query = _normalise_query(query)
        # Build the ordered list of instances to try: configured one first.
        primary = settings.searxng_base_url.rstrip("/")
        instances = [primary] + [
            u for u in _SEARXNG_FALLBACK_INSTANCES if u.rstrip("/") != primary
        ]

        # Use the shorter per-instance timeout so dead nodes fail fast.
        with httpx.Client(
            timeout=settings.searxng_instance_timeout,
            follow_redirects=True,
        ) as client:
            for base in instances:
                try:
                    urls = self._query_instance(client, base, query, max_results)
                    if urls:
                        print(f"[SearXNG] ✓ {base} → {len(urls)} result(s).")
                        return urls
                    print(f"[SearXNG] {base} returned 0 results, trying next instance.")
                except Exception as exc:
                    print(f"[SearXNG] {base} failed: {exc!r:.120}, trying next instance.")

        print("[SearXNG] all instances exhausted.")
        return []


# ---------------------------------------------------------------------------
# DuckDuckGo provider (with exponential backoff)
# ---------------------------------------------------------------------------

class DuckDuckGoProvider(SearchProvider):
    """Wrapper around ``duckduckgo_search.DDGS`` with retry on rate-limit."""

    @property
    def name(self) -> str:
        return "DuckDuckGo"

    def search(self, query: str, max_results: int = 5) -> list[str]:
        query = _normalise_query(query)
        base_delay = settings.search_retry_base_delay
        max_retries = settings.search_retry_max

        for attempt in range(max_retries + 1):
            try:
                with DDGS() as ddgs:
                    results = ddgs.text(query, max_results=max_results)
                urls = [r["href"] for r in results if "href" in r]
                if urls:
                    print(f"[DuckDuckGo] ✓ {len(urls)} result(s).")
                return urls
            except RatelimitException:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(
                        f"[DuckDuckGo] rate-limited (attempt {attempt + 1}/{max_retries}); "
                        f"retrying in {delay:.0f}s …"
                    )
                    time.sleep(delay)
                else:
                    print(f"[DuckDuckGo] exhausted {max_retries} retries — rate-limited.")
                    return []
            except DuckDuckGoSearchException as exc:
                print(f"[DuckDuckGo] search error: {exc}")
                return []
            except Exception as exc:
                msg = str(exc)
                is_ratelimit = "202" in msg or "Ratelimit" in msg or "ratelimit" in msg.lower()
                if is_ratelimit and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(
                        f"[DuckDuckGo] rate-limit detected (attempt {attempt + 1}/{max_retries}); "
                        f"retrying in {delay:.0f}s …"
                    )
                    time.sleep(delay)
                    continue
                print(f"[DuckDuckGo] error: {exc}")
                return []

        return []


# ---------------------------------------------------------------------------
# Provider chain
# ---------------------------------------------------------------------------

class SearchProviderChain:
    """Try providers in order; return the first non-empty result list."""

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    def search(self, query: str, max_results: int = 5) -> list[str]:
        for provider in self._providers:
            urls = provider.search(query, max_results=max_results)
            if urls:
                return urls
        print("[search chain] all providers returned no results.")
        return []


# ---------------------------------------------------------------------------
# Default chain factory
# ---------------------------------------------------------------------------

def build_default_chain() -> SearchProviderChain:
    """Brave (if key) → SearXNG → DuckDuckGo.

    Brave leads because it is the fastest and most reliable.  SearXNG is tried
    next with a short per-instance timeout.  DuckDuckGo is the last resort.
    """
    providers: list[SearchProvider] = []
    if settings.brave_api_key:
        providers.append(BraveSearchProvider())
    providers.append(SearXNGProvider())
    providers.append(DuckDuckGoProvider())
    return SearchProviderChain(providers)
