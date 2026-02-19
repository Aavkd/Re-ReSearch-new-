"""Keyword, vector, and hybrid search over the knowledge base.

Search modes
------------
``fts_search``
    Full-text search via SQLite FTS5 (porter-stemmed keyword match).

``vector_search``
    K-nearest-neighbour lookup via sqlite-vec (cosine-style L2 distance).

``hybrid_search``
    Merges FTS and vector results, deduplicates, and re-ranks by a simple
    reciprocal-rank fusion (RRF) score.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import sqlite_vec

from backend.db.models import Node
from backend.db.nodes import _row_to_node


# ---------------------------------------------------------------------------
# FTS5 keyword search
# ---------------------------------------------------------------------------

def fts_search(conn: sqlite3.Connection, query: str, top_k: int = 10) -> list[Node]:
    """Return up to *top_k* nodes whose indexed text matches *query*.

    Uses FTS5 ``MATCH`` with an implicit prefix match; the porter tokeniser
    handles stemming.

    Args:
        conn: Open DB connection (sqlite-vec loaded).
        query: Free-text search string.
        top_k: Maximum number of results to return.

    Returns:
        A list of :class:`~backend.db.models.Node` objects ordered by FTS5
        relevance (``bm25``).
    """
    rows = conn.execute(
        """
        SELECT n.*
        FROM   nodes n
        JOIN   nodes_fts f ON n.id = f.id
        WHERE  nodes_fts MATCH ?
        ORDER  BY bm25(nodes_fts)
        LIMIT  ?
        """,
        (query, top_k),
    ).fetchall()
    return [_row_to_node(r) for r in rows]


# ---------------------------------------------------------------------------
# Vector (sqlite-vec) search
# ---------------------------------------------------------------------------

def vector_search(
    conn: sqlite3.Connection,
    embedding: list[float],
    top_k: int = 10,
) -> list[Node]:
    """Return the *top_k* nodes closest to *embedding* in vector space.

    Args:
        conn: Open DB connection (sqlite-vec loaded and ``nodes_vec`` populated).
        embedding: Query vector of length ``settings.embedding_dim``.
        top_k: Number of nearest neighbours to return.

    Returns:
        Nodes ordered by ascending L2 distance (closest first).
    """
    blob = sqlite_vec.serialize_float32(embedding)
    rows = conn.execute(
        """
        SELECT n.*, v.distance
        FROM   nodes_vec v
        JOIN   nodes n ON n.id = v.id
        WHERE  v.embedding MATCH ?
          AND  k = ?
        ORDER  BY v.distance
        """,
        (blob, top_k),
    ).fetchall()
    return [_row_to_node(r) for r in rows]


# ---------------------------------------------------------------------------
# Hybrid search (RRF re-ranking)
# ---------------------------------------------------------------------------

def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    embedding: list[float],
    top_k: int = 10,
    rrf_k: int = 60,
) -> list[Node]:
    """Merge FTS and vector results using Reciprocal Rank Fusion (RRF).

    RRF score for a document *d*:
        score(d) = Σ  1 / (rrf_k + rank_i(d))

    where *rank_i* is the 1-based rank of *d* in result list *i*.

    Args:
        conn: Open DB connection.
        query: Keyword query (passed to :func:`fts_search`).
        embedding: Query vector (passed to :func:`vector_search`).
        top_k: Number of final results to return.
        rrf_k: RRF smoothing constant (default 60 per literature).

    Returns:
        Deduplicated, re-ranked list of :class:`~backend.db.models.Node`.
    """
    fts_results = fts_search(conn, query, top_k=top_k * 2)
    vec_results = vector_search(conn, embedding, top_k=top_k * 2)

    scores: dict[str, float] = {}
    id_to_node: dict[str, Node] = {}

    for rank, node in enumerate(fts_results, start=1):
        scores[node.id] = scores.get(node.id, 0.0) + 1.0 / (rrf_k + rank)
        id_to_node[node.id] = node

    for rank, node in enumerate(vec_results, start=1):
        scores[node.id] = scores.get(node.id, 0.0) + 1.0 / (rrf_k + rank)
        id_to_node[node.id] = node

    ranked_ids = sorted(scores, key=lambda nid: scores[nid], reverse=True)
    return [id_to_node[nid] for nid in ranked_ids[:top_k]]
