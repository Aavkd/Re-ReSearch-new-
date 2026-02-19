"""Search endpoint — FTS5, vector, and hybrid modes.

Routes
------
GET /search?q=<query>&mode=fuzzy|semantic|hybrid&top_k=10
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request

from backend.db.search import fts_search, hybrid_search, vector_search

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_dict(node) -> dict[str, Any]:  # type: ignore[type-arg]
    return {
        "id": node.id,
        "node_type": node.node_type,
        "title": node.title,
        "content_path": node.content_path,
        "metadata": node.metadata,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("")
def search(
    request: Request,
    q: str,
    mode: Literal["fuzzy", "semantic", "hybrid"] = "fuzzy",
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search the knowledge base.

    Args:
        q: Search query string.
        mode: ``fuzzy`` uses FTS5 keyword matching; ``semantic`` uses vector
            KNN; ``hybrid`` combines both with reciprocal-rank fusion.
        top_k: Maximum number of results to return.
    """
    conn = request.app.state.db

    if mode == "fuzzy":
        nodes = fts_search(conn, q, top_k=top_k)
        return [_node_dict(n) for n in nodes]

    # semantic / hybrid — require the embedder
    try:
        from backend.rag.embedder import embed_text  # noqa: PLC0415

        embedding = embed_text(q)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Embedding service unavailable ({exc}). "
                "Use mode=fuzzy or ensure Ollama / OpenAI is reachable."
            ),
        ) from exc

    if mode == "semantic":
        nodes = vector_search(conn, embedding, top_k=top_k)
    else:  # hybrid
        nodes = hybrid_search(conn, q, embedding, top_k=top_k)

    return [_node_dict(n) for n in nodes]
