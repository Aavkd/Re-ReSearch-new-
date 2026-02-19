"""Operations on the ``edges`` table."""

from __future__ import annotations

import sqlite3
from time import time

from backend.db.models import Edge, GraphPayload, Node
from backend.db.nodes import _row_to_node


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def connect_nodes(
    conn: sqlite3.Connection,
    source_id: str,
    target_id: str,
    relation_type: str = "related",
) -> None:
    """Create a directed edge from *source* to *target*.

    Uses ``INSERT OR IGNORE`` so calling it twice with the same triple is safe.
    """
    now = int(time())
    with conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO edges (source_id, target_id, relation_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, target_id, relation_type, now),
        )


def get_edges(conn: sqlite3.Connection, node_id: str) -> list[Edge]:
    """Return all edges where *node_id* is the source **or** the target."""
    rows = conn.execute(
        """
        SELECT source_id, target_id, relation_type, created_at
        FROM   edges
        WHERE  source_id = ? OR target_id = ?
        """,
        (node_id, node_id),
    ).fetchall()
    return [
        Edge(
            source_id=r["source_id"],
            target_id=r["target_id"],
            relation_type=r["relation_type"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def get_graph_data(conn: sqlite3.Connection) -> GraphPayload:
    """Return **all** nodes and edges — intended for graph visualisation.

    Returns:
        A :class:`~backend.db.models.GraphPayload` with ``nodes`` and
        ``edges`` lists populated.
    """
    node_rows = conn.execute("SELECT * FROM nodes ORDER BY created_at DESC").fetchall()
    edge_rows = conn.execute(
        "SELECT source_id, target_id, relation_type, created_at FROM edges"
    ).fetchall()

    nodes: list[Node] = [_row_to_node(r) for r in node_rows]
    edges: list[Edge] = [
        Edge(
            source_id=r["source_id"],
            target_id=r["target_id"],
            relation_type=r["relation_type"],
            created_at=r["created_at"],
        )
        for r in edge_rows
    ]
    return GraphPayload(nodes=nodes, edges=edges)
