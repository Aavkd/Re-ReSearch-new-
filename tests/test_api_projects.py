"""Tests for the /projects API endpoints (Phase 14).

All tests use an in-memory SQLite database via the FastAPI TestClient.
No network or Ollama/OpenAI calls are made.
"""

from __future__ import annotations

import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.db.connection import get_connection
from backend.db.migrations import init_db
from backend.db.nodes import create_node


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Return a TestClient backed by an isolated in-memory DB.

    The TestClient lifespan creates its own DB connection when the context
    manager enters.  We immediately replace it with a fresh in-memory
    connection so each test is fully isolated from the on-disk workspace DB.
    """
    conn = get_connection(db_path=":memory:")  # type: ignore[arg-type]
    init_db(conn)
    app = create_app()

    with TestClient(app, raise_server_exceptions=True) as c:
        # Lifespan has run by this point; override its db with our in-memory one.
        c.app.state.db = conn
        yield c

    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_project(client, name: str) -> dict:
    resp = client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_empty_list(self, client):
        resp = client.get("/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_projects(self, client):
        _create_project(client, "P1")
        _create_project(client, "P2")
        resp = client.get("/projects")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()]
        assert "P1" in titles
        assert "P2" in titles


class TestCreateProject:
    def test_creates_project_node(self, client):
        resp = client.post("/projects", json={"name": "New Project"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Project"
        assert data["node_type"] == "Project"
        assert "id" in data

    def test_returns_valid_id(self, client):
        resp = client.post("/projects", json={"name": "X"})
        assert resp.status_code == 201
        assert len(resp.json()["id"]) == 36  # UUID format


class TestGetProjectSummary:
    def test_returns_summary(self, client):
        project = _create_project(client, "Summary Test")
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "by_type" in data
        assert "recent_artifacts" in data

    def test_empty_project_has_zero_nodes(self, client):
        project = _create_project(client, "Empty Project")
        resp = client.get(f"/projects/{project['id']}")
        assert resp.json()["total_nodes"] == 0

    def test_404_for_unknown_project(self, client):
        resp = client.get("/projects/does-not-exist-id")
        assert resp.status_code == 404


class TestGetProjectNodes:
    def test_returns_linked_nodes(self, client):
        project = _create_project(client, "Node Test")

        # Link a node via /projects/{id}/link
        conn = client.app.state.db  # type: ignore[attr-defined]
        source = create_node(conn, title="Source 1", node_type="Source")
        link_resp = client.post(
            f"/projects/{project['id']}/link",
            json={"node_id": source.id, "relation": "HAS_SOURCE"},
        )
        assert link_resp.status_code == 201

        resp = client.get(f"/projects/{project['id']}/nodes")
        assert resp.status_code == 200
        ids = [n["id"] for n in resp.json()]
        assert source.id in ids

    def test_404_for_unknown_project(self, client):
        resp = client.get("/projects/no-such-id/nodes")
        assert resp.status_code == 404


class TestGetProjectGraph:
    def test_returns_nodes_and_edges_keys(self, client):
        project = _create_project(client, "Graph Test")
        resp = client.get(f"/projects/{project['id']}/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_project_root_included_in_nodes(self, client):
        project = _create_project(client, "Root Included")
        resp = client.get(f"/projects/{project['id']}/graph")
        ids = [n["id"] for n in resp.json()["nodes"]]
        assert project["id"] in ids

    def test_linked_node_appears_in_graph(self, client):
        project = _create_project(client, "Graph Link Test")
        conn = client.app.state.db  # type: ignore[attr-defined]
        source = create_node(conn, title="Linked Source", node_type="Source")
        client.post(
            f"/projects/{project['id']}/link",
            json={"node_id": source.id, "relation": "HAS_SOURCE"},
        )
        resp = client.get(f"/projects/{project['id']}/graph")
        ids = [n["id"] for n in resp.json()["nodes"]]
        assert source.id in ids
        relations = [e["relation_type"] for e in resp.json()["edges"]]
        assert "HAS_SOURCE" in relations

    def test_404_for_unknown_project(self, client):
        resp = client.get("/projects/no-such-id/graph")
        assert resp.status_code == 404


class TestLinkNodeToProject:
    def test_link_creates_edge(self, client):
        project = _create_project(client, "Link Test")
        conn = client.app.state.db  # type: ignore[attr-defined]
        node = create_node(conn, title="Article", node_type="Source")

        resp = client.post(
            f"/projects/{project['id']}/link",
            json={"node_id": node.id, "relation": "HAS_SOURCE"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] == project["id"]
        assert data["node_id"] == node.id
        assert data["relation"] == "HAS_SOURCE"

    def test_node_appears_in_project_nodes_after_link(self, client):
        project = _create_project(client, "Link Appears")
        conn = client.app.state.db  # type: ignore[attr-defined]
        node = create_node(conn, title="Appears Node", node_type="Artifact")
        client.post(
            f"/projects/{project['id']}/link",
            json={"node_id": node.id, "relation": "HAS_ARTIFACT"},
        )
        resp = client.get(f"/projects/{project['id']}/nodes")
        ids = [n["id"] for n in resp.json()]
        assert node.id in ids

    def test_404_for_unknown_project(self, client):
        resp = client.post(
            "/projects/no-such-id/link",
            json={"node_id": "any", "relation": "HAS_SOURCE"},
        )
        assert resp.status_code == 404

    def test_404_for_unknown_node(self, client):
        project = _create_project(client, "Link 404 Node")
        resp = client.post(
            f"/projects/{project['id']}/link",
            json={"node_id": "no-such-node", "relation": "HAS_SOURCE"},
        )
        assert resp.status_code == 404


class TestExportProject:
    def test_export_returns_nodes_and_edges(self, client):
        project = _create_project(client, "Export Test")
        resp = client.get(f"/projects/{project['id']}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "project" in data
        assert "nodes" in data
        assert "edges" in data

    def test_export_project_metadata(self, client):
        project = _create_project(client, "Export Meta")
        resp = client.get(f"/projects/{project['id']}/export")
        assert resp.json()["project"]["name"] == "Export Meta"
        assert resp.json()["project"]["id"] == project["id"]

    def test_404_for_unknown_project(self, client):
        resp = client.get("/projects/no-such-id/export")
        assert resp.status_code == 404


class TestCorsHeaders:
    def test_cors_headers_present_on_options(self, client):
        resp = client.options(
            "/projects",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        # CORS middleware responds to preflight
        assert resp.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")

    def test_cors_header_present_on_get(self, client):
        resp = client.get("/projects", headers={"Origin": "http://localhost:3000"})
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "*"
