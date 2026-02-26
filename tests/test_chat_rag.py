"""Phase B-C2 tests — RAG chat streaming service.

All LLM calls, embedding calls, and DB search calls are mocked so these
tests run without any network connections or database state.

pytest-asyncio is configured with ``asyncio_mode = "auto"`` in pyproject.toml,
so ``async def`` test methods are picked up automatically.
"""

from __future__ import annotations

import json
import sqlite3
from typing import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import settings
from backend.db.connection import get_connection
from backend.db.migrations import init_db
from backend.db.models import Node
from backend.rag.chat import chat_stream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_EMBEDDING: list[float] = [0.1] * settings.embedding_dim


def _make_node(node_id: str = "node-1", title: str = "Source A") -> Node:
    return Node(
        id=node_id,
        node_type="Chunk",
        title=title,
        content_path=None,
        metadata={"text": "Relevant content.", "url": "https://example.com"},
        created_at=1700000000,
        updated_at=1700000000,
    )


async def _make_astream(*tokens: str):
    """Async generator that yields fake LLM chunk objects."""
    for token in tokens:
        chunk = MagicMock()
        chunk.content = token
        yield chunk


def _parse_events(sse_frames: list[str]) -> list[dict]:
    """Parse a list of SSE frame strings into their JSON payloads."""
    events = []
    for frame in sse_frames:
        frame = frame.strip()
        if frame.startswith("data: "):
            events.append(json.loads(frame[len("data: "):]))
    return events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn() -> Generator[sqlite3.Connection, None, None]:
    connection = get_connection(db_path=":memory:")  # type: ignore[arg-type]
    init_db(connection)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChatStream:
    async def test_chat_stream_yields_token_then_citation_then_done(
        self, conn: sqlite3.Connection
    ) -> None:
        """Happy path: token events, then citation, then done."""
        fake_node = _make_node()

        mock_llm = MagicMock()
        mock_llm.astream.return_value = _make_astream("Hello", " world")

        with (
            patch("backend.rag.chat.embed_text", return_value=FAKE_EMBEDDING),
            patch("backend.rag.chat.hybrid_search", return_value=[fake_node]),
            patch("backend.rag.chat._get_llm", return_value=mock_llm),
        ):
            frames = [
                frame
                async for frame in chat_stream(conn, "What is X?", history=[])
            ]

        events = _parse_events(frames)
        event_types = [e["event"] for e in events]

        # Must contain at least one token before citation and done
        assert "token" in event_types
        assert "citation" in event_types
        assert "done" in event_types

        # Order: all tokens come first, then citation, then done
        first_citation_idx = event_types.index("citation")
        first_done_idx = event_types.index("done")
        last_token_idx = max(
            i for i, et in enumerate(event_types) if et == "token"
        )
        assert last_token_idx < first_citation_idx < first_done_idx

        # Token content is correct
        token_texts = [e["text"] for e in events if e["event"] == "token"]
        assert token_texts == ["Hello", " world"]

        # Citation payload references the fake node
        citation_event = next(e for e in events if e["event"] == "citation")
        assert citation_event["nodes"][0]["id"] == fake_node.id
        assert citation_event["nodes"][0]["title"] == fake_node.title

    async def test_chat_stream_no_results_yields_fallback(
        self, conn: sqlite3.Connection
    ) -> None:
        """When hybrid_search is empty, no citation event is emitted."""
        mock_llm = MagicMock()
        mock_llm.astream.return_value = _make_astream("I don't know.")

        with (
            patch("backend.rag.chat.embed_text", return_value=FAKE_EMBEDDING),
            patch("backend.rag.chat.hybrid_search", return_value=[]),
            patch("backend.rag.chat._get_llm", return_value=mock_llm),
        ):
            frames = [
                frame
                async for frame in chat_stream(conn, "Unknown topic", history=[])
            ]

        events = _parse_events(frames)
        event_types = [e["event"] for e in events]

        assert "token" in event_types
        assert "citation" not in event_types
        assert "done" in event_types

    async def test_chat_stream_scoped_to_project(
        self, conn: sqlite3.Connection
    ) -> None:
        """When project_id is supplied, get_project_nodes is called."""
        fake_node = _make_node()
        project_node = _make_node(node_id="proj-1", title="Project Node")

        mock_llm = MagicMock()
        mock_llm.astream.return_value = _make_astream("Answer.")

        with (
            patch("backend.rag.chat.embed_text", return_value=FAKE_EMBEDDING),
            patch(
                "backend.rag.chat.get_project_nodes", return_value=[project_node]
            ) as mock_get_project_nodes,
            patch("backend.rag.chat.hybrid_search", return_value=[fake_node]) as mock_search,
            patch("backend.rag.chat._get_llm", return_value=mock_llm),
        ):
            frames = [
                frame
                async for frame in chat_stream(
                    conn, "Scoped question", history=[], project_id="proj-1"
                )
            ]

        # Verify scoping was applied
        mock_get_project_nodes.assert_called_once_with(conn, "proj-1", depth=3)
        call_kwargs = mock_search.call_args
        assert call_kwargs.kwargs.get("scope_ids") == [project_node.id] or \
               (call_kwargs.args and call_kwargs.args[-1] == [project_node.id]) or \
               "proj-1" in str(call_kwargs)

        events = _parse_events(frames)
        event_types = [e["event"] for e in events]
        assert "done" in event_types

    async def test_chat_stream_passes_history_to_llm(
        self, conn: sqlite3.Connection
    ) -> None:
        """History turns are forwarded to the LLM as prior messages."""
        mock_llm = MagicMock()
        mock_llm.astream.return_value = _make_astream("Continued answer.")

        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]

        captured_messages: list = []

        async def capture_astream(messages):
            captured_messages.extend(messages)
            yield MagicMock(content="Continued answer.")

        mock_llm.astream = capture_astream

        with (
            patch("backend.rag.chat.embed_text", return_value=FAKE_EMBEDDING),
            patch("backend.rag.chat.hybrid_search", return_value=[]),
            patch("backend.rag.chat._get_llm", return_value=mock_llm),
        ):
            _ = [
                frame
                async for frame in chat_stream(
                    conn, "Follow-up question", history=history
                )
            ]

        # System message + 2 history turns + current question = 4 messages
        assert len(captured_messages) == 4

    async def test_chat_stream_yields_error_on_exception(
        self, conn: sqlite3.Connection
    ) -> None:
        """Exceptions inside the generator are surfaced as error events."""
        with (
            patch(
                "backend.rag.chat.embed_text",
                side_effect=RuntimeError("embedding service down"),
            ),
        ):
            frames = [
                frame
                async for frame in chat_stream(conn, "Any question", history=[])
            ]

        events = _parse_events(frames)
        assert len(events) == 1
        assert events[0]["event"] == "error"
        assert "embedding service down" in events[0]["detail"]
