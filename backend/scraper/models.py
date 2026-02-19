"""Data models for the scraper pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RawPage:
    """The raw HTTP response for a single URL fetch."""

    url: str
    html: str
    status_code: int


@dataclass
class CleanPage:
    """Cleaned, readable content extracted from a :class:`RawPage`."""

    url: str
    title: str
    text: str
    links: List[str] = field(default_factory=list)
