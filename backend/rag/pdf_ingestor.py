"""RAG ingestion pipeline — PDF variant.

``ingest_pdf`` accepts a local PDF path and follows the same chunk → embed →
store pipeline as :mod:`backend.rag.ingestor`, replacing the web-fetch step
with ``pypdf`` text extraction.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import sqlite_vec

from backend.config import settings
from backend.db.edges import connect_nodes
from backend.db.models import Node
from backend.db.nodes import create_node
from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed_text


def _extract_pdf_text(path: str | Path) -> str:
    """Return all text extracted from *path* using ``pypdf``.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ImportError: If ``pypdf`` is not installed.
    """
    import pypdf  # noqa: PLC0415 — lazy import keeps startup fast

    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = pypdf.PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    return "\n\n".join(pages)


def ingest_pdf(conn: sqlite3.Connection, path: str | Path) -> Node:
    """Extract text from a PDF file, chunk it, embed each chunk, and persist.

    Pipeline mirrors :func:`~backend.rag.ingestor.ingest_url` from step 3
    onwards:

        extract text (pypdf) → create Source node → update FTS →
        chunk → embed → create Chunk nodes → insert embeddings → edges

    Args:
        conn: Open, initialised DB connection (sqlite-vec loaded).
        path: Absolute or relative path to the PDF file on disk.

    Returns:
        The newly created ``Source`` :class:`~backend.db.models.Node`.
    """
    pdf_path = Path(path)

    # ------------------------------------------------------------------
    # Extract text from the PDF
    # ------------------------------------------------------------------
    full_text = _extract_pdf_text(pdf_path)

    # ------------------------------------------------------------------
    # Create the Source node
    # ------------------------------------------------------------------
    source_node = create_node(
        conn,
        title=pdf_path.stem,
        node_type="Source",
        metadata={
            "path": str(pdf_path.resolve()),
            "word_count": len(full_text.split()),
            "source_type": "pdf",
        },
    )

    # ------------------------------------------------------------------
    # Update FTS with the full extracted text
    # ------------------------------------------------------------------
    with conn:
        conn.execute(
            "UPDATE nodes_fts SET content_body = ? WHERE id = ?",
            (full_text, source_node.id),
        )

    # ------------------------------------------------------------------
    # Chunk, embed, and store
    # ------------------------------------------------------------------
    chunks = chunk_text(full_text, settings.chunk_size, settings.chunk_overlap)

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk)

        chunk_node = create_node(
            conn,
            title=f"{pdf_path.stem} [chunk {i + 1}/{total}]",
            node_type="Chunk",
            metadata={
                "source_id": source_node.id,
                "chunk_index": i,
                "text": chunk,
                "source_type": "pdf",
            },
        )

        # Persist chunk text in FTS.
        with conn:
            conn.execute(
                "UPDATE nodes_fts SET content_body = ? WHERE id = ?",
                (chunk, chunk_node.id),
            )

        # Upsert embedding into nodes_vec.
        blob = sqlite_vec.serialize_float32(embedding)
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes_vec(id, embedding) VALUES (?, ?)",
                (chunk_node.id, blob),
            )

        # Edge: source → chunk
        connect_nodes(conn, source_node.id, chunk_node.id, relation_type="has_chunk")

    return source_node
