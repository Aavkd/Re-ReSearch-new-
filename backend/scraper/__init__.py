"""Scraper package — web fetch & content extraction."""

from backend.scraper.extractor import extract_content
from backend.scraper.fetcher import fetch_url
from backend.scraper.models import CleanPage, RawPage

__all__ = ["fetch_url", "extract_content", "RawPage", "CleanPage"]
