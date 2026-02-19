"""Callable tools used by the LangGraph node functions.

Each function has a simple, focused signature so that node closures can call
them directly.  The ``scrape_and_ingest`` and ``rag_retrieve`` helpers require
an open DB connection which is captured by the node factory closures in
``backend.agent.nodes``.
"""

from __future__ import annotations

import sqlite3

from duckduckgo_search import DDGS

from backend.db.search import fts_search, hybrid_search
from backend.rag.embedder import embed_text
from backend.rag.ingestor import ingest_url


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------

def web_search(query: str, max_results: int = 5) -> list[str]:
    """Search DuckDuckGo and return a list of result URLs.

    Args:
        query: Search query string.
        max_results: Maximum number of URLs to return (DuckDuckGo may return
            fewer if insufficient results exist).

    Returns:
        A list of URL strings (possibly empty if the search fails).
    """
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)

    return [r["href"] for r in results if "href" in r]


# ---------------------------------------------------------------------------
# Scrape & ingest
# ---------------------------------------------------------------------------

def scrape_and_ingest(conn: sqlite3.Connection, url: str) -> str:
    """Fetch *url*, ingest it into the knowledge base, and return a summary.

    Args:
        conn: Open, initialised DB connection.
        url: The web page to scrape.

    Returns:
        A one-line human-readable summary of what was ingested, e.g.
        ``"Ingested: 'Page Title' (1 234 words)"``.

    Raises:
        Any exception raised by the scraper or ingestor propagates to the
        caller so the scraper node can log it and continue.
    """
    node = ingest_url(conn, url)
    word_count = node.metadata.get("word_count", 0)
    return f"Ingested: {node.title!r} ({word_count} words)"


# ---------------------------------------------------------------------------
# RAG retrieval
# ---------------------------------------------------------------------------

def rag_retrieve(conn: sqlite3.Connection, query: str, top_k: int = 5) -> str:
    """Retrieve the most relevant chunks from the knowledge base.

    Tries hybrid (FTS + vector) search first; falls back to FTS-only if the
    embedder is unavailable (e.g. Ollama is not running).

    Args:
        conn: Open, initialised DB connection.
        query: Natural-language query.
        top_k: Number of chunks to include in the result.

    Returns:
        A formatted string containing the retrieved chunks, ready to be
        injected into an LLM prompt.  Returns a "no results" message when the
        knowledge base is empty.
    """
    nodes = []
    try:
        embedding = embed_text(query)
        nodes = hybrid_search(conn, query, embedding, top_k=top_k)
    except Exception:
        # Embedder unavailable — degrade gracefully to keyword search.
        nodes = fts_search(conn, query, top_k=top_k)

    if not nodes:
        return "No relevant content found in the knowledge base."

    parts: list[str] = []
    for node in nodes:
        chunk_text = node.metadata.get("text", "")
        if chunk_text:
            parts.append(f"[{node.node_type}] {node.title}\n{chunk_text}")
        else:
            parts.append(f"[{node.node_type}] {node.title}")

    return "\n\n---\n\n".join(parts)
