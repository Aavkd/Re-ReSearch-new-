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
# FTS5 helpers
# ---------------------------------------------------------------------------

import re as _re

def _sanitize_fts_query(text: str) -> str:
    """Convert a natural-language string into a safe FTS5 query expression.

    FTS5 treats commas, apostrophes, hyphens, colons, quotes, and other
    punctuation as query operators, which causes ``OperationalError: fts5:
    syntax error`` when a raw sentence is used as the match term.

    Strategy: extract individual word tokens (≥3 chars), wrap each in
    double-quotes (FTS5 treats quoted strings as phrase literals), and join
    them with spaces (implicit AND).  Returns ``"*"`` (match everything) if
    no tokens survive so the call never hard-errors.
    """
    tokens = _re.findall(r"[A-Za-z0-9]{3,}", text)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique = [t for t in tokens if not (t.lower() in seen or seen.add(t.lower()))]  # type: ignore[func-returns-value]
    if not unique:
        return '"*"'
    return " ".join(f'"{t}"' for t in unique)


# ---------------------------------------------------------------------------
# FTS5 keyword search
# ---------------------------------------------------------------------------

def fts_search(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 10,
    scope_ids: Optional[list[str]] = None,
) -> list[Node]:
    """Return up to *top_k* nodes whose indexed text matches *query*.

    If scope_ids is provided, filter results to only those IDs.
    """
    fts_query = _sanitize_fts_query(query)

    scope_clause = ""
    params: list = [fts_query]

    if scope_ids:
        placeholders = ",".join("?" for _ in scope_ids)
        scope_clause = f"AND n.id IN ({placeholders})"
        params.extend(scope_ids)

    params.append(top_k)

    query_sql = f"""
        SELECT n.*
        FROM   nodes n
        JOIN   nodes_fts f ON n.id = f.id
        WHERE  nodes_fts MATCH ?
        {scope_clause}
        ORDER  BY bm25(nodes_fts)
        LIMIT  ?
    """

    rows = conn.execute(query_sql, params).fetchall()
    return [_row_to_node(r) for r in rows]


# ---------------------------------------------------------------------------
# Vector (sqlite-vec) search
# ---------------------------------------------------------------------------

def vector_search(
    conn: sqlite3.Connection,
    embedding: list[float],
    top_k: int = 10,
    scope_ids: Optional[list[str]] = None
) -> list[Node]:
    """Return the *top_k* nodes closest to *embedding* in vector space.
    
    If scope_ids is provided, filter results to only those IDs.
    Note: sqlite-vec filtering capabilities might be limited.
    We might need to fetch more and filter in Python if sqlite-vec doesn't support IN clause easily.
    Currently sqlite-vec supports `k = ?` and `embedding MATCH ?`.
    Adding arbitrary WHERE clauses on the main table join works but might be slow if vector index is used first.
    
    However, sqlite-vec `vec0` table is virtual.
    Efficient pre-filtering is hard. Post-filtering is easier.
    """
    blob = sqlite_vec.serialize_float32(embedding)
    
    # Strategy: Fetch top_k * 5 candidates, filter in Python if scope_ids is set.
    # Why? Passing IN clause to virtual table query might not be optimized or supported for pre-filtering.
    # Actually, we can join and filter.
    
    scope_clause = ""
    params = [blob, top_k] # Start with standard params
    
    if scope_ids:
        # If filtering, fetch more candidates to ensure we have enough after filtering
        # Or let SQL do it if possible.
        # Let's try simple SQL filtering after join.
        placeholders = ",".join("?" for _ in scope_ids)
        scope_clause = f"AND n.id IN ({placeholders})"
        # We need to inject these params before the LIMIT/k?
        # No, k is a parameter to the MATCH constraint usually, or hidden.
        # sqlite-vec uses `k = ?` as a constraint on the virtual table scan.
        
        # We can't easily put `IN` params inside the query string if we are using list injection for `scope_ids`
        # and `blob` is also a param.
        # Let's append scope_ids to params.
        params.extend(scope_ids)
    
    query_sql = f"""
        SELECT n.*, v.distance
        FROM   nodes_vec v
        JOIN   nodes n ON n.id = v.id
        WHERE  v.embedding MATCH ?
          AND  k = ?
          {scope_clause}
        ORDER  BY v.distance
    """
    
    rows = conn.execute(query_sql, params).fetchall()
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
    scope_ids: Optional[list[str]] = None
) -> list[Node]:
    """Merge FTS and vector results using Reciprocal Rank Fusion (RRF)."""
    
    # Pass scope_ids down
    fts_results = fts_search(conn, query, top_k=top_k * 2, scope_ids=scope_ids)
    vec_results = vector_search(conn, embedding, top_k=top_k * 2, scope_ids=scope_ids)

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
