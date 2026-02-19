"""CRUD operations for the ``nodes`` table."""

from __future__ import annotations

import json
import sqlite3
import uuid
from time import time
from typing import Any, Optional

from backend.db.models import Node


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _row_to_node(row: sqlite3.Row) -> Node:
    return Node(
        id=row["id"],
        node_type=row["node_type"],
        title=row["title"],
        content_path=row["content_path"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_node(
    conn: sqlite3.Connection,
    title: str,
    node_type: str,
    metadata: Optional[dict[str, Any]] = None,
    content_path: Optional[str] = None,
    node_id: Optional[str] = None,
) -> Node:
    """Insert a new node and return it.

    Args:
        conn: Open DB connection.
        title: Human-readable display name.
        node_type: One of ``Artifact``, ``Source``, ``Concept``, ``Chat``,
            ``Image``, or any custom string.
        metadata: Arbitrary key/value pairs stored as a JSON blob.
        content_path: Optional relative path to a file on disk.
        node_id: Explicit UUID override (auto-generated when omitted).

    Returns:
        The newly created :class:`~backend.db.models.Node`.
    """
    nid = node_id or str(uuid.uuid4())
    now = int(time())
    meta_json = json.dumps(metadata or {})

    with conn:
        conn.execute(
            """
            INSERT INTO nodes (id, node_type, title, content_path, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (nid, node_type, title, content_path, meta_json, now, now),
        )

    return get_node(conn, nid)  # type: ignore[return-value]


def get_node(conn: sqlite3.Connection, node_id: str) -> Optional[Node]:
    """Fetch a single node by its UUID.  Returns ``None`` if not found."""
    row = conn.execute(
        "SELECT * FROM nodes WHERE id = ?", (node_id,)
    ).fetchone()
    return _row_to_node(row) if row else None


def update_node(conn: sqlite3.Connection, node_id: str, **kwargs: Any) -> Node:
    """Update one or more fields on a node.

    Allowed keyword arguments: ``title``, ``node_type``, ``content_path``,
    ``metadata`` (dict).  ``updated_at`` is always refreshed automatically.

    Raises:
        ValueError: If ``node_id`` does not exist or no valid fields are given.
    """
    # Validate that the node exists
    if get_node(conn, node_id) is None:
        raise ValueError(f"Node not found: {node_id!r}")

    allowed = {"title", "node_type", "content_path", "metadata"}
    updates: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key not in allowed:
            raise ValueError(f"Cannot update field {key!r}")
        if key == "metadata":
            updates["metadata"] = json.dumps(value)
        else:
            updates[key] = value

    if not updates:
        raise ValueError("No valid fields provided to update_node()")

    updates["updated_at"] = int(time())
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [node_id]

    with conn:
        conn.execute(
            f"UPDATE nodes SET {set_clause} WHERE id = ?", values  # noqa: S608
        )

    return get_node(conn, node_id)  # type: ignore[return-value]


def delete_node(conn: sqlite3.Connection, node_id: str) -> None:
    """Delete a node (and its edges via CASCADE).

    This is a no-op if the node does not exist.
    """
    with conn:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))


def list_nodes(
    conn: sqlite3.Connection,
    node_type: Optional[str] = None,
) -> list[Node]:
    """Return all nodes, optionally filtered by ``node_type``."""
    if node_type:
        rows = conn.execute(
            "SELECT * FROM nodes WHERE node_type = ? ORDER BY created_at DESC",
            (node_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM nodes ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_node(r) for r in rows]
