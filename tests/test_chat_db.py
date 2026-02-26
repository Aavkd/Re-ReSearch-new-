"""Phase B-C1 tests — Chat database layer.

All tests use an in-memory SQLite database so they are:
- Fast (no disk I/O)
- Isolated (each fixture gets a fresh DB)
- Side-effect free (nothing written to ~/.research_data)
"""

from __future__ import annotations

import sqlite3
from typing import Generator

import pytest

from backend.db.connection import get_connection
from backend.db.edges import get_edges
from backend.db.migrations import init_db
from backend.db.nodes import get_node
from backend.db.projects import create_project
from backend.db.chat import (
    append_messages,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn() -> Generator[sqlite3.Connection, None, None]:
    """In-memory connection with schema initialised."""
    connection = get_connection(db_path=":memory:")  # type: ignore[arg-type]
    init_db(connection)
    yield connection
    connection.close()


@pytest.fixture()
def project(conn: sqlite3.Connection):
    """A bare Project node in *conn*."""
    return create_project(conn, "Test Project")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateConversation:
    def test_create_conversation_creates_node_and_edge(
        self, conn: sqlite3.Connection, project
    ) -> None:
        conv = create_conversation(conn, project.id, title="My chat")

        # Node exists with correct type and title
        assert conv.node_type == "Chat"
        assert conv.title == "My chat"
        assert conv.metadata["messages"] == []

        # Edge CONVERSATION_IN exists: Chat → Project
        edges = get_edges(conn, conv.id)
        matching = [
            e for e in edges
            if e.source_id == conv.id
            and e.target_id == project.id
            and e.relation_type == "CONVERSATION_IN"
        ]
        assert len(matching) == 1

    def test_default_title_is_set(self, conn: sqlite3.Connection, project) -> None:
        conv = create_conversation(conn, project.id)
        assert conv.title == "New conversation"

    def test_returns_node_with_id(self, conn: sqlite3.Connection, project) -> None:
        conv = create_conversation(conn, project.id)
        assert conv.id  # non-empty string
        assert get_node(conn, conv.id) is not None


class TestGetConversation:
    def test_returns_none_for_missing_id(self, conn: sqlite3.Connection) -> None:
        assert get_conversation(conn, "no-such-id") is None

    def test_returns_none_for_non_chat_node(
        self, conn: sqlite3.Connection, project
    ) -> None:
        # project is a Project node, not a Chat node
        assert get_conversation(conn, project.id) is None

    def test_returns_correct_node(self, conn: sqlite3.Connection, project) -> None:
        conv = create_conversation(conn, project.id, title="Fetch test")
        fetched = get_conversation(conn, conv.id)
        assert fetched is not None
        assert fetched.id == conv.id
        assert fetched.title == "Fetch test"


class TestListConversations:
    def test_list_conversations_scoped_to_project(
        self, conn: sqlite3.Connection
    ) -> None:
        p1 = create_project(conn, "Project 1")
        p2 = create_project(conn, "Project 2")

        c1 = create_conversation(conn, p1.id, title="Conv in P1")
        c2 = create_conversation(conn, p1.id, title="Conv in P1 #2")
        _c3 = create_conversation(conn, p2.id, title="Conv in P2")  # noqa: F841

        convs_p1 = list_conversations(conn, p1.id)
        ids_p1 = {c.id for c in convs_p1}
        assert c1.id in ids_p1
        assert c2.id in ids_p1
        assert len(convs_p1) == 2

        convs_p2 = list_conversations(conn, p2.id)
        assert len(convs_p2) == 1

    def test_empty_when_no_conversations(
        self, conn: sqlite3.Connection, project
    ) -> None:
        assert list_conversations(conn, project.id) == []

    def test_ordered_by_updated_at_desc(
        self, conn: sqlite3.Connection, project
    ) -> None:
        c1 = create_conversation(conn, project.id, title="First")
        # Append a message to c1 so its updated_at is bumped above c2's
        c2 = create_conversation(conn, project.id, title="Second")
        append_messages(conn, c1.id, [{"role": "user", "content": "hi", "ts": 1}])

        convs = list_conversations(conn, project.id)
        # c1 was updated after c2 was created, so it should appear first
        assert convs[0].id == c1.id


class TestAppendMessages:
    def test_append_messages_updates_metadata(
        self, conn: sqlite3.Connection, project
    ) -> None:
        conv = create_conversation(conn, project.id)
        msg = {"role": "user", "content": "Hello!", "ts": 1700000000}

        updated = append_messages(conn, conv.id, [msg])

        assert updated.metadata["messages"] == [msg]

    def test_multiple_appends_accumulate(
        self, conn: sqlite3.Connection, project
    ) -> None:
        conv = create_conversation(conn, project.id)
        m1 = {"role": "user", "content": "Msg 1", "ts": 1}
        m2 = {"role": "assistant", "content": "Msg 2", "ts": 2}
        m3 = {"role": "user", "content": "Msg 3", "ts": 3}

        append_messages(conn, conv.id, [m1, m2])
        updated = append_messages(conn, conv.id, [m3])

        assert updated.metadata["messages"] == [m1, m2, m3]

    def test_raises_for_missing_conversation(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="Chat node not found"):
            append_messages(conn, "no-such-id", [])


class TestDeleteConversation:
    def test_delete_conversation_cascades(
        self, conn: sqlite3.Connection, project
    ) -> None:
        conv = create_conversation(conn, project.id)
        conv_id = conv.id

        # Verify edge exists before deletion
        edges_before = get_edges(conn, conv_id)
        assert len(edges_before) > 0

        delete_conversation(conn, conv_id)

        # Node is gone
        assert get_node(conn, conv_id) is None

        # Edges referencing the node are also gone (CASCADE)
        edges_after = get_edges(conn, conv_id)
        assert edges_after == []

    def test_delete_noop_for_missing_id(self, conn: sqlite3.Connection) -> None:
        # Should not raise
        delete_conversation(conn, "nonexistent-id")
