"""RAG ingestion pipeline — URL variant.

``ingest_url`` orchestrates the full pipeline from a raw URL to a populated
knowledge base:

    fetch → extract → create Source node → chunk → embed → store chunks
"""

from __future__ import annotations

import sqlite3

import sqlite_vec

from backend.config import settings
from backend.db.edges import connect_nodes
from backend.db.models import Node
from backend.db.nodes import create_node
from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed_text
from backend.scraper.extractor import extract_content
from backend.scraper.fetcher import fetch_url


def ingest_url(conn: sqlite3.Connection, url: str) -> Node:
    """Scrape *url*, chunk its text, embed each chunk, and persist everything.

    Pipeline:
        1. :func:`~backend.scraper.fetcher.fetch_url` — HTTP fetch (Playwright
           fallback for SPAs).
        2. :func:`~backend.scraper.extractor.extract_content` — readability
           extraction.
        3. Create a ``Source`` node in the DB.
        4. Update the FTS row for the source node with the full extracted text.
        5. :func:`~backend.rag.chunker.chunk_text` — split into overlapping
           character chunks.
        6. :func:`~backend.rag.embedder.embed_text` — embed each chunk.
        7. Create a ``Chunk`` node per chunk, persist its FTS content, and
           insert its embedding into ``nodes_vec``.
        8. Create a ``has_chunk`` edge from the Source to each Chunk node.

    Args:
        conn: Open, initialised DB connection (sqlite-vec loaded).
        url: The web page URL to ingest.

    Returns:
        The newly created ``Source`` :class:`~backend.db.models.Node`.
    """
    # ------------------------------------------------------------------
    # 1 & 2 — Fetch and extract
    # ------------------------------------------------------------------
    raw = fetch_url(url)
    clean = extract_content(raw)

    # ------------------------------------------------------------------
    # 3 — Create the Source node
    # ------------------------------------------------------------------
    source_node = create_node(
        conn,
        title=clean.title or url,
        node_type="Source",
        metadata={
            "url": url,
            "word_count": len(clean.text.split()),
            "links_count": len(clean.links),
        },
    )

    # ------------------------------------------------------------------
    # 4 — Update FTS with the full extracted text
    # The nodes_ai trigger already inserted a blank row; we UPDATE it.
    # ------------------------------------------------------------------
    with conn:
        conn.execute(
            "UPDATE nodes_fts SET content_body = ? WHERE id = ?",
            (clean.text, source_node.id),
        )

    # ------------------------------------------------------------------
    # 5 — Chunk
    # ------------------------------------------------------------------
    chunks = chunk_text(clean.text, settings.chunk_size, settings.chunk_overlap)

    # ------------------------------------------------------------------
    # 6 & 7 — Embed each chunk and store in DB
    # ------------------------------------------------------------------
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk)

        # Create a Chunk node; its text is stored in metadata for retrieval.
        chunk_node = create_node(
            conn,
            title=f"{clean.title or url} [chunk {i + 1}/{total}]",
            node_type="Chunk",
            metadata={
                "source_id": source_node.id,
                "chunk_index": i,
                "text": chunk,
            },
        )

        # Persist chunk text in FTS so keyword search finds individual chunks.
        with conn:
            conn.execute(
                "UPDATE nodes_fts SET content_body = ? WHERE id = ?",
                (chunk, chunk_node.id),
            )

        # Upsert embedding — INSERT OR REPLACE handles re-ingestion cleanly.
        blob = sqlite_vec.serialize_float32(embedding)
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes_vec(id, embedding) VALUES (?, ?)",
                (chunk_node.id, blob),
            )

        # 8 — Edge: source → chunk
        connect_nodes(conn, source_node.id, chunk_node.id, relation_type="has_chunk")

    return source_node
