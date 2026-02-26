"""CRUD helpers for Chat nodes and their message payloads.

A Chat node is a regular node with ``node_type="Chat"``.  Messages are stored
as a JSON array in ``metadata["messages"]``.  A directed edge with relation
type ``CONVERSATION_IN`` connects the Chat node (source) to its Project node
(target).

Message dict shape::

    {
        "role": "user" | "assistant",
        "content": "...",
        "ts": 1700000000   # Unix timestamp (int)
    }
"""

from __future__ import annotations

import sqlite3
from time import time
from typing import Any

from backend.db.edges import connect_nodes
from backend.db.models import Node
from backend.db.nodes import create_node, delete_node, get_node, update_node


# Relation type used to link a Chat node back to its project root
_CONV_RELATION = "CONVERSATION_IN"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_conversation(
    conn: sqlite3.Connection,
    project_id: str,
    title: str = "New conversation",
) -> Node:
    """Create a Chat node and link it to *project_id*.

    Args:
        conn: Open DB connection.
        project_id: UUID of the parent Project node.
        title: Human-readable conversation title.

    Returns:
        The newly created Chat :class:`~backend.db.models.Node`.
    """
    node = create_node(
        conn,
        title=title,
        node_type="Chat",
        metadata={"messages": []},
    )
    # Edge: Chat → Project  (CONVERSATION_IN)
    connect_nodes(conn, node.id, project_id, _CONV_RELATION)
    return node


def get_conversation(conn: sqlite3.Connection, conv_id: str) -> Node | None:
    """Fetch a single Chat node by *conv_id*.  Returns ``None`` if not found."""
    node = get_node(conn, conv_id)
    if node is None or node.node_type != "Chat":
        return None
    return node


def list_conversations(conn: sqlite3.Connection, project_id: str) -> list[Node]:
    """Return all Chat nodes linked to *project_id* via ``CONVERSATION_IN``.

    Results are ordered by ``updated_at DESC`` (most recently active first).
    """
    rows = conn.execute(
        """
        SELECT n.*
        FROM   nodes  AS n
        JOIN   edges  AS e ON e.source_id = n.id
        WHERE  n.node_type     = 'Chat'
          AND  e.relation_type = ?
          AND  e.target_id     = ?
        ORDER  BY n.updated_at DESC
        """,
        (_CONV_RELATION, project_id),
    ).fetchall()

    result: list[Node] = []
    for row in rows:
        import json

        result.append(
            Node(
                id=row["id"],
                node_type=row["node_type"],
                title=row["title"],
                content_path=row["content_path"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return result


def append_messages(
    conn: sqlite3.Connection,
    conv_id: str,
    messages: list[dict[str, Any]],
) -> Node:
    """Merge *messages* into ``metadata.messages`` and refresh ``updated_at``.

    Args:
        conn: Open DB connection.
        conv_id: UUID of the Chat node.
        messages: List of message dicts (``role``, ``content``, ``ts``).

    Returns:
        The updated Chat :class:`~backend.db.models.Node`.

    Raises:
        ValueError: If *conv_id* does not correspond to a Chat node.
    """
    node = get_conversation(conn, conv_id)
    if node is None:
        raise ValueError(f"Chat node not found: {conv_id!r}")

    existing: list[dict[str, Any]] = node.metadata.get("messages", [])
    updated_messages = existing + messages
    new_metadata = {**node.metadata, "messages": updated_messages}

    return update_node(conn, conv_id, metadata=new_metadata)


def delete_conversation(conn: sqlite3.Connection, conv_id: str) -> None:
    """Delete a Chat node (and its edges via CASCADE).

    This is a no-op if *conv_id* does not exist.
    """
    delete_node(conn, conv_id)
