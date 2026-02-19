"""Dataclass models representing DB rows.

These are plain Python objects – not ORM models.  The DB layer serialises /
deserialises to and from these types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    id: str
    node_type: str
    title: str
    content_path: str | None
    metadata: dict[str, Any]
    created_at: int
    updated_at: int

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def metadata_json(self) -> str:
        """Serialise metadata dict to a JSON string for storage."""
        return json.dumps(self.metadata)


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation_type: str
    created_at: int


@dataclass
class GraphPayload:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
