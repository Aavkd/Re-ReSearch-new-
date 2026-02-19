"""Phase 1 tests — database layer.

All tests use an in-memory SQLite database so they are:
- Fast (no disk I/O)
- Isolated (each fixture gets a fresh DB)
- Side-effect free (nothing written to ~/.research_data)

sqlite-vec must be installed (``pip install sqlite-vec``).
"""

from __future__ import annotations

import sqlite3
from typing import Generator

import pytest
import sqlite_vec

from backend.config import settings
from backend.db.connection import get_connection
from backend.db.edges import connect_nodes, get_edges, get_graph_data
from backend.db.migrations import current_version, init_db
from backend.db.models import Node
from backend.db.nodes import (
    create_node,
    delete_node,
    get_node,
    list_nodes,
    update_node,
)
from backend.db.search import fts_search, hybrid_search, vector_search


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn() -> Generator[sqlite3.Connection, None, None]:
    """In-memory connection with sqlite-vec loaded and schema initialised."""
    connection = get_connection(db_path=":memory:")  # type: ignore[arg-type]
    init_db(connection)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# connection / init
# ---------------------------------------------------------------------------

class TestConnection:
    def test_sqlite_vec_loaded(self, conn: sqlite3.Connection) -> None:
        """sqlite-vec should expose vec_version()."""
        row = conn.execute("SELECT vec_version()").fetchone()
        assert row is not None
        assert row[0]  # non-empty string

    def test_foreign_keys_enabled(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1

    def test_wal_mode(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        # In-memory DBs always return 'memory', on-disk returns 'wal'
        assert row[0] in ("wal", "memory")


class TestInitDb:
    def test_tables_exist(self, conn: sqlite3.Connection) -> None:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow')"
            ).fetchall()
        }
        assert "nodes" in tables
        assert "edges" in tables

    def test_version_table_exists(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        assert row is not None

    def test_current_version_zero_on_fresh_db(self, conn: sqlite3.Connection) -> None:
        assert current_version(conn) == 0

    def test_init_db_is_idempotent(self, conn: sqlite3.Connection) -> None:
        # Calling init_db a second time must not raise
        init_db(conn)


# ---------------------------------------------------------------------------
# Nodes CRUD
# ---------------------------------------------------------------------------

class TestNodesCrud:
    def test_create_node_returns_node(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Hello", node_type="Artifact")
        assert isinstance(node, Node)
        assert node.title == "Hello"
        assert node.node_type == "Artifact"
        assert node.id  # non-empty UUID

    def test_create_node_metadata_roundtrip(self, conn: sqlite3.Connection) -> None:
        meta = {"tags": ["ai", "test"], "source_url": "https://example.com"}
        node = create_node(conn, title="Meta Test", node_type="Source", metadata=meta)
        assert node.metadata["tags"] == ["ai", "test"]
        assert node.metadata["source_url"] == "https://example.com"

    def test_create_node_defaults_empty_metadata(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="No Meta", node_type="Concept")
        assert node.metadata == {}

    def test_get_node_found(self, conn: sqlite3.Connection) -> None:
        created = create_node(conn, title="Fetch Me", node_type="Artifact")
        fetched = get_node(conn, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_node_not_found(self, conn: sqlite3.Connection) -> None:
        assert get_node(conn, "nonexistent-uuid") is None

    def test_update_node_title(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Old Title", node_type="Artifact")
        updated = update_node(conn, node.id, title="New Title")
        assert updated.title == "New Title"
        assert updated.updated_at >= node.updated_at

    def test_update_node_metadata(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Update Meta", node_type="Artifact")
        updated = update_node(conn, node.id, metadata={"key": "value"})
        assert updated.metadata == {"key": "value"}

    def test_update_node_invalid_field_raises(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Bad Update", node_type="Artifact")
        with pytest.raises(ValueError, match="Cannot update field"):
            update_node(conn, node.id, nonexistent_field="x")

    def test_update_nonexistent_node_raises(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="Node not found"):
            update_node(conn, "fake-id", title="x")

    def test_delete_node(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Delete Me", node_type="Artifact")
        delete_node(conn, node.id)
        assert get_node(conn, node.id) is None

    def test_delete_node_noop_on_missing(self, conn: sqlite3.Connection) -> None:
        # Should not raise
        delete_node(conn, "not-there")

    def test_list_nodes_all(self, conn: sqlite3.Connection) -> None:
        create_node(conn, title="A", node_type="Artifact")
        create_node(conn, title="B", node_type="Source")
        nodes = list_nodes(conn)
        assert len(nodes) == 2

    def test_list_nodes_filtered(self, conn: sqlite3.Connection) -> None:
        create_node(conn, title="Art", node_type="Artifact")
        create_node(conn, title="Src", node_type="Source")
        artifacts = list_nodes(conn, node_type="Artifact")
        assert all(n.node_type == "Artifact" for n in artifacts)
        assert len(artifacts) == 1

    def test_list_nodes_empty(self, conn: sqlite3.Connection) -> None:
        assert list_nodes(conn) == []


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

class TestEdges:
    def test_connect_nodes(self, conn: sqlite3.Connection) -> None:
        a = create_node(conn, "A", "Concept")
        b = create_node(conn, "B", "Concept")
        connect_nodes(conn, a.id, b.id, "mentions")
        edges = get_edges(conn, a.id)
        assert len(edges) == 1
        assert edges[0].source_id == a.id
        assert edges[0].target_id == b.id

    def test_connect_nodes_idempotent(self, conn: sqlite3.Connection) -> None:
        a = create_node(conn, "A", "Concept")
        b = create_node(conn, "B", "Concept")
        connect_nodes(conn, a.id, b.id, "related")
        connect_nodes(conn, a.id, b.id, "related")  # second call must not raise
        assert len(get_edges(conn, a.id)) == 1

    def test_get_edges_returns_both_directions(self, conn: sqlite3.Connection) -> None:
        a = create_node(conn, "A", "Concept")
        b = create_node(conn, "B", "Concept")
        connect_nodes(conn, a.id, b.id)
        # get_edges for b should also return the edge where b is the target
        edges_b = get_edges(conn, b.id)
        assert len(edges_b) == 1

    def test_edge_cascade_delete(self, conn: sqlite3.Connection) -> None:
        a = create_node(conn, "A", "Concept")
        b = create_node(conn, "B", "Concept")
        connect_nodes(conn, a.id, b.id)
        delete_node(conn, a.id)
        edges = get_edges(conn, b.id)
        assert edges == []

    def test_get_graph_data(self, conn: sqlite3.Connection) -> None:
        a = create_node(conn, "A", "Concept")
        b = create_node(conn, "B", "Concept")
        connect_nodes(conn, a.id, b.id)
        graph = get_graph_data(conn)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1


# ---------------------------------------------------------------------------
# FTS5 search
# ---------------------------------------------------------------------------

class TestFtsSearch:
    def test_fts_returns_matching_node(self, conn: sqlite3.Connection) -> None:
        create_node(conn, title="Solid State Battery", node_type="Source")
        create_node(conn, title="Quantum Computing", node_type="Source")
        results = fts_search(conn, "battery")
        assert len(results) == 1
        assert "Battery" in results[0].title

    def test_fts_no_results(self, conn: sqlite3.Connection) -> None:
        create_node(conn, title="Unrelated Topic", node_type="Artifact")
        results = fts_search(conn, "zygomorphic")
        assert results == []

    def test_fts_porter_stemming(self, conn: sqlite3.Connection) -> None:
        """'batteries' should match a node titled 'battery' via porter stemmer."""
        create_node(conn, title="battery technology", node_type="Source")
        results = fts_search(conn, "batteries")
        assert len(results) == 1

    def test_fts_node_deleted_removed_from_index(self, conn: sqlite3.Connection) -> None:
        node = create_node(conn, title="Ephemeral", node_type="Artifact")
        delete_node(conn, node.id)
        assert fts_search(conn, "Ephemeral") == []


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------

class TestVectorSearch:
    """Vector search tests use fixed small embeddings — no Ollama required."""

    @staticmethod
    def _make_embedding(dim: int, value: float) -> list[float]:
        return [value] * dim

    def test_vector_search_returns_closest_node(self, conn: sqlite3.Connection) -> None:
        dim = settings.embedding_dim
        node = create_node(conn, title="Vector Node", node_type="Source")

        embedding = self._make_embedding(dim, 1.0)
        blob = sqlite_vec.serialize_float32(embedding)
        with conn:
            conn.execute(
                "INSERT INTO nodes_vec(id, embedding) VALUES (?, ?)",
                (node.id, blob),
            )

        results = vector_search(conn, embedding, top_k=5)
        assert len(results) == 1
        assert results[0].id == node.id

    def test_vector_search_empty_table(self, conn: sqlite3.Connection) -> None:
        dim = settings.embedding_dim
        q = self._make_embedding(dim, 0.5)
        results = vector_search(conn, q, top_k=5)
        assert results == []

    def test_vector_search_top_k_respected(self, conn: sqlite3.Connection) -> None:
        dim = settings.embedding_dim
        for i in range(5):
            n = create_node(conn, title=f"VNode{i}", node_type="Source")
            emb = self._make_embedding(dim, float(i) * 0.1)
            blob = sqlite_vec.serialize_float32(emb)
            with conn:
                conn.execute(
                    "INSERT INTO nodes_vec(id, embedding) VALUES (?, ?)", (n.id, blob)
                )

        q = self._make_embedding(dim, 0.0)
        results = vector_search(conn, q, top_k=3)
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------

class TestHybridSearch:
    def test_hybrid_merges_results(self, conn: sqlite3.Connection) -> None:
        dim = settings.embedding_dim
        # Node that only appears in FTS
        fts_only = create_node(conn, title="Electrolyte Chemistry", node_type="Source")
        # Node that only appears in vector
        vec_only = create_node(conn, title="Completely Unrelated Title", node_type="Source")

        emb = [1.0] * dim
        blob = sqlite_vec.serialize_float32(emb)
        with conn:
            conn.execute(
                "INSERT INTO nodes_vec(id, embedding) VALUES (?, ?)",
                (vec_only.id, blob),
            )

        results = hybrid_search(conn, "electrolyte", emb, top_k=10)
        result_ids = {n.id for n in results}
        assert fts_only.id in result_ids
        assert vec_only.id in result_ids

    def test_hybrid_deduplicates(self, conn: sqlite3.Connection) -> None:
        dim = settings.embedding_dim
        node = create_node(conn, title="Solid State Battery", node_type="Source")
        emb = [1.0] * dim
        blob = sqlite_vec.serialize_float32(emb)
        with conn:
            conn.execute(
                "INSERT INTO nodes_vec(id, embedding) VALUES (?, ?)",
                (node.id, blob),
            )

        results = hybrid_search(conn, "battery", emb, top_k=10)
        ids = [n.id for n in results]
        assert len(ids) == len(set(ids)), "Duplicate node IDs in hybrid results"
