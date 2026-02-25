"""RAG-based question answering scoped to a project.

``recall`` retrieves relevant chunks from the knowledge base (optionally
filtered to the active project), synthesises them into a prompt, and calls
the configured LLM to produce a grounded answer with source citations.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.config import settings
from backend.db.projects import get_project_nodes
from backend.db.search import hybrid_search
from backend.rag.embedder import embed_text


# ---------------------------------------------------------------------------
# LLM helper (mirrors backend/agent/nodes.py)
# ---------------------------------------------------------------------------

def _get_llm() -> Any:
    """Return a configured LangChain chat model based on ``settings``."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_chat_model, temperature=0)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_chat_model, temperature=0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recall(
    conn: sqlite3.Connection,
    question: str,
    project_id: str | None = None,
    top_k: int = 5,
) -> str:
    """Answer *question* using chunks from the knowledge base.

    Steps:
        1. Resolve the node IDs that belong to the active project (if
           ``project_id`` is given) so the search is scoped.
        2. Embed the question.
        3. ``hybrid_search`` with the scope filter to retrieve the most
           relevant ``Chunk`` nodes.
        4. Format the chunks as context and call the LLM.
        5. Return the formatted answer with source citations.

    Args:
        conn: Open, initialised DB connection.
        question: The natural-language question to answer.
        project_id: If provided, restrict retrieval to nodes reachable from
            this project root.  ``None`` means search the entire knowledge
            base.
        top_k: Number of chunks to retrieve.

    Returns:
        A string containing the LLM's answer followed by a *Sources* section
        listing the titles of the retrieved nodes.

    Raises:
        RuntimeError: If the LLM call fails.
    """
    # ------------------------------------------------------------------
    # 1 — Resolve scope
    # ------------------------------------------------------------------
    scope_ids: list[str] | None = None
    if project_id:
        project_nodes = get_project_nodes(conn, project_id, depth=3)
        scope_ids = [n.id for n in project_nodes] if project_nodes else []

    # ------------------------------------------------------------------
    # 2 — Embed the question
    # ------------------------------------------------------------------
    question_vec = embed_text(question)

    # ------------------------------------------------------------------
    # 3 — Hybrid retrieval
    # ------------------------------------------------------------------
    results = hybrid_search(
        conn,
        question,
        question_vec,
        top_k=top_k,
        scope_ids=scope_ids if scope_ids else None,
    )

    if not results:
        return "No relevant sources found in the knowledge base."

    # ------------------------------------------------------------------
    # 4 — Build LLM prompt from retrieved chunks
    # ------------------------------------------------------------------
    context_parts: list[str] = []
    sources: list[str] = []

    for i, node in enumerate(results, start=1):
        # Chunks store their text in metadata["text"]; Source nodes store
        # it in the FTS index.  We use the title as a fallback.
        chunk_text_content = (
            node.metadata.get("text", "")
            if node.metadata
            else ""
        )
        display = chunk_text_content or node.title
        context_parts.append(f"[{i}] {display}")
        sources.append(f"[{i}] {node.title}")

    context_block = "\n\n".join(context_parts)
    prompt = (
        "You are a research assistant. Answer the question below using ONLY the "
        "provided sources. Cite sources by their number (e.g. [1], [2]). "
        "If the sources do not contain enough information to answer, say so.\n\n"
        f"Sources:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    # ------------------------------------------------------------------
    # 5 — Call LLM
    # ------------------------------------------------------------------
    llm = _get_llm()
    response = llm.invoke(prompt)
    answer = response.content if hasattr(response, "content") else str(response)

    # ------------------------------------------------------------------
    # 6 — Append citations
    # ------------------------------------------------------------------
    sources_section = "\n".join(sources)
    return f"{answer.strip()}\n\nSources:\n{sources_section}"
