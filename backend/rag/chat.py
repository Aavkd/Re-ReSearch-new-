"""Multi-turn, citation-aware RAG chat as an async streaming generator.

``chat_stream`` retrieves relevant knowledge-base chunks, builds a
conversation-aware prompt, streams LLM tokens, and finally emits citation
and done events — all via SSE-formatted strings that the router can forward
directly to the browser.

SSE event shapes
----------------
Every yielded string is a self-contained SSE frame::

    data: {"event": "token",    "text": " ..."}\\n\\n
    data: {"event": "citation", "nodes": [{"id":"...", "title":"...", "url":"..."}]}\\n\\n
    data: {"event": "done"}\\n\\n
    data: {"event": "error",    "detail": "..."}\\n\\n
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, AsyncIterator

from backend.config import settings
from backend.db.projects import get_project_nodes
from backend.db.search import hybrid_search
from backend.rag.embedder import embed_text


# ---------------------------------------------------------------------------
# Maximum history turns to include (avoids overflowing context window)
# ---------------------------------------------------------------------------
_MAX_HISTORY_TURNS = 10


# ---------------------------------------------------------------------------
# LLM helper (mirrors recall.py)
# ---------------------------------------------------------------------------

def _get_llm() -> Any:
    """Return a streaming-capable LangChain chat model from ``settings``."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_chat_model, temperature=0, streaming=True)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_chat_model, temperature=0)


def _sse(payload: dict) -> str:
    """Encode *payload* as a single SSE frame (``data: ...\\n\\n``)."""
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def chat_stream(
    conn: sqlite3.Connection,
    question: str,
    history: list[dict],
    project_id: str | None = None,
    top_k: int = 5,
) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for a single chat turn.

    Args:
        conn: Open, initialised DB connection.
        question: The user's latest message.
        history: Prior ``{"role": "user"|"assistant", "content": "..."}``
            turns used as conversation context.
        project_id: Scopes retrieval to this project's knowledge base.
            ``None`` means search the entire knowledge base.
        top_k: Number of chunks to retrieve.

    Yields:
        SSE-formatted strings (see module docstring for shapes).
    """
    try:
        # ------------------------------------------------------------------
        # 1 — Resolve project scope
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

        # ------------------------------------------------------------------
        # 4 — Build prompt
        # ------------------------------------------------------------------
        context_parts: list[str] = []
        citation_nodes: list[dict] = []

        for i, node in enumerate(results, start=1):
            chunk_content = (
                node.metadata.get("text", "") if node.metadata else ""
            )
            display = chunk_content or node.title
            context_parts.append(f"[{i}] {display}")
            citation_nodes.append(
                {
                    "id": node.id,
                    "title": node.title,
                    "url": node.metadata.get("url", "") if node.metadata else "",
                }
            )

        if context_parts:
            context_block = "\n\n".join(context_parts)
            system_content = (
                "You are a research assistant. Answer the user's question using "
                "ONLY the provided sources. Cite sources by their number "
                "(e.g. [1], [2]). If the sources do not contain enough "
                "information to answer, say so.\n\n"
                f"Sources:\n{context_block}"
            )
        else:
            system_content = (
                "You are a research assistant. "
                "No relevant sources were found in the knowledge base for this "
                "question. Politely let the user know and offer general guidance "
                "if possible."
            )

        # Build LangChain message list
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages: list[Any] = [SystemMessage(content=system_content)]

        # Include the last _MAX_HISTORY_TURNS turns from history
        trimmed_history = history[-(_MAX_HISTORY_TURNS * 2):]
        for turn in trimmed_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        # Append the current question
        lc_messages.append(HumanMessage(content=question))

        # ------------------------------------------------------------------
        # 5–6 — Stream LLM tokens
        # ------------------------------------------------------------------
        llm = _get_llm()
        async for chunk in llm.astream(lc_messages):
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if text:
                yield _sse({"event": "token", "text": text})

        # ------------------------------------------------------------------
        # 7 — Emit citations (only when sources were found)
        # ------------------------------------------------------------------
        if citation_nodes:
            yield _sse({"event": "citation", "nodes": citation_nodes})

        # ------------------------------------------------------------------
        # 8 — Done
        # ------------------------------------------------------------------
        yield _sse({"event": "done"})

    except Exception as exc:  # noqa: BLE001
        yield _sse({"event": "error", "detail": str(exc)})
