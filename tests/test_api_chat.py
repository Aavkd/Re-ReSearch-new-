"""Phase B-C3 tests — Chat API router.

All tests use an in-memory SQLite database via the FastAPI TestClient.
LLM / embedding calls are mocked so no external services are required.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.db.connection import get_connection
from backend.db.migrations import init_db
from backend.db.projects import create_project


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fake_chat_stream(*args, **kwargs):
    """Minimal async generator that emits one token, one citation, and done."""
    yield 'data: {"event": "token", "text": "Hello"}\n\n'
    yield 'data: {"event": "citation", "nodes": [{"id": "n1", "title": "Src", "url": ""}]}\n\n'
    yield 'data: {"event": "done"}\n\n'


def _parse_sse(content: bytes) -> list[dict]:
    """Parse raw SSE response bytes into a list of event dicts."""
    events = []
    for line in content.decode().splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[len("data: "):]))
            except json.JSONDecodeError:
                pass
    return events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """TestClient backed by an isolated in-memory DB."""
    conn = get_connection(db_path=":memory:")  # type: ignore[arg-type]
    init_db(conn)
    app = create_app()

    with TestClient(app, raise_server_exceptions=True) as c:
        c.app.state.db = conn
        yield c

    conn.close()


@pytest.fixture()
def project(client: TestClient) -> dict:
    """Create a project and return its JSON payload."""
    resp = client.post("/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def conversation(client: TestClient, project: dict) -> dict:
    """Create a conversation for *project* and return its JSON payload."""
    pid = project["id"]
    resp = client.post(f"/projects/{pid}/chat", json={"title": "Test Conv"})
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateAndListConversation:
    def test_create_conversation_returns_201(self, client: TestClient, project: dict):
        pid = project["id"]
        resp = client.post(f"/projects/{pid}/chat", json={"title": "My Chat"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Chat"
        assert data["messages"] == []
        assert "id" in data

    def test_create_conversation_default_title(self, client: TestClient, project: dict):
        pid = project["id"]
        resp = client.post(f"/projects/{pid}/chat", json={})
        assert resp.status_code == 201
        assert resp.json()["title"] == "New conversation"

    def test_list_conversations_returns_all(
        self, client: TestClient, project: dict
    ):
        pid = project["id"]
        client.post(f"/projects/{pid}/chat", json={"title": "A"})
        client.post(f"/projects/{pid}/chat", json={"title": "B"})

        resp = client.get(f"/projects/{pid}/chat")
        assert resp.status_code == 200
        titles = {c["title"] for c in resp.json()}
        assert {"A", "B"}.issubset(titles)

    def test_list_conversations_scoped_to_project(
        self, client: TestClient, project: dict
    ):
        pid = project["id"]
        other = client.post("/projects", json={"name": "Other"}).json()
        oid = other["id"]

        client.post(f"/projects/{pid}/chat", json={"title": "Mine"})
        client.post(f"/projects/{oid}/chat", json={"title": "Theirs"})

        resp = client.get(f"/projects/{pid}/chat")
        titles = [c["title"] for c in resp.json()]
        assert "Mine" in titles
        assert "Theirs" not in titles

    def test_list_conversations_unknown_project_returns_404(
        self, client: TestClient
    ):
        resp = client.get("/projects/no-such-id/chat")
        assert resp.status_code == 404

    def test_create_conversation_unknown_project_returns_404(
        self, client: TestClient
    ):
        resp = client.post("/projects/no-such-id/chat", json={"title": "X"})
        assert resp.status_code == 404


class TestGetConversation:
    def test_get_conversation_returns_messages(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]
        resp = client.get(f"/projects/{pid}/chat/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cid
        assert isinstance(data["messages"], list)

    def test_get_conversation_unknown_conv_returns_404(
        self, client: TestClient, project: dict
    ):
        pid = project["id"]
        resp = client.get(f"/projects/{pid}/chat/no-such-conv")
        assert resp.status_code == 404

    def test_get_conversation_unknown_project_returns_404(
        self, client: TestClient
    ):
        resp = client.get("/projects/no-such-id/chat/any-conv")
        assert resp.status_code == 404


class TestPostMessage:
    def test_post_message_streams_sse(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]

        with patch("backend.api.routers.chat.chat_stream", side_effect=_fake_chat_stream):
            resp = client.post(
                f"/projects/{pid}/chat/{cid}/messages",
                json={"message": "Hello?", "history": []},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        events = _parse_sse(resp.content)
        event_types = [e["event"] for e in events]
        assert "token" in event_types
        assert "done" in event_types

    def test_post_message_persists_user_and_assistant(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]

        with patch("backend.api.routers.chat.chat_stream", side_effect=_fake_chat_stream):
            client.post(
                f"/projects/{pid}/chat/{cid}/messages",
                json={"message": "What is X?", "history": []},
            )

        # Verify messages were persisted
        resp = client.get(f"/projects/{pid}/chat/{cid}")
        messages = resp.json()["messages"]
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    def test_post_message_contains_token_and_done_events(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]

        with patch("backend.api.routers.chat.chat_stream", side_effect=_fake_chat_stream):
            resp = client.post(
                f"/projects/{pid}/chat/{cid}/messages",
                json={"message": "Test", "history": []},
            )

        events = _parse_sse(resp.content)

        token_events = [e for e in events if e["event"] == "token"]
        assert len(token_events) >= 1
        assert token_events[0]["text"] == "Hello"

        assert events[-1]["event"] == "done"

    def test_post_message_404_unknown_project(self, client: TestClient):
        resp = client.post(
            "/projects/no-such-id/chat/any-conv/messages",
            json={"message": "Hi"},
        )
        assert resp.status_code == 404

    def test_post_message_404_unknown_conversation(
        self, client: TestClient, project: dict
    ):
        pid = project["id"]
        resp = client.post(
            f"/projects/{pid}/chat/no-such-conv/messages",
            json={"message": "Hi"},
        )
        assert resp.status_code == 404


class TestDeleteConversation:
    def test_delete_conversation_returns_204(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]
        resp = client.delete(f"/projects/{pid}/chat/{cid}")
        assert resp.status_code == 204

    def test_delete_conversation_removes_it_from_list(
        self, client: TestClient, project: dict, conversation: dict
    ):
        pid = project["id"]
        cid = conversation["id"]
        client.delete(f"/projects/{pid}/chat/{cid}")

        resp = client.get(f"/projects/{pid}/chat")
        ids = [c["id"] for c in resp.json()]
        assert cid not in ids

    def test_delete_conversation_404_unknown_conv(
        self, client: TestClient, project: dict
    ):
        pid = project["id"]
        resp = client.delete(f"/projects/{pid}/chat/no-such-conv")
        assert resp.status_code == 404

    def test_delete_conversation_404_unknown_project(self, client: TestClient):
        resp = client.delete("/projects/no-such-id/chat/any-conv")
        assert resp.status_code == 404
