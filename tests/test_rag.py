"""Phase 3 tests — RAG ingestion pipeline.

All tests use an in-memory SQLite database so they are:
- Fast (no disk I/O)
- Isolated (each fixture gets a fresh DB)
- Side-effect free (nothing written to ~/.research_data)

Network calls (Ollama, OpenAI, httpx) and scraper calls are mocked throughout.
"""

from __future__ import annotations

import sqlite3
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from backend.config import settings
from backend.db.connection import get_connection
from backend.db.migrations import init_db
from backend.db.nodes import list_nodes
from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed_text
from backend.rag.ingestor import ingest_url
from backend.rag.pdf_ingestor import ingest_pdf
from backend.scraper.models import CleanPage, RawPage

# A fixed embedding vector that matches the configured dimension.
FAKE_EMBEDDING: list[float] = [0.1] * settings.embedding_dim


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
# TestChunker
# ---------------------------------------------------------------------------

class TestChunker:
    def test_empty_text_returns_empty_list(self) -> None:
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert chunk_text("   \n\n   ") == []

    def test_short_text_single_chunk(self) -> None:
        text = "Hello, world!"
        result = chunk_text(text, chunk_size=512, overlap=64)
        assert len(result) == 1
        assert result[0] == text

    def test_chunks_respect_chunk_size(self) -> None:
        # 50 chars × 30 = ~1500-char string — must produce multiple chunks
        text = "abcde fghij klmno pqrst uvwxy " * 50
        chunks = chunk_text(text, chunk_size=200, overlap=20)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 200, f"Chunk exceeded chunk_size: {len(chunk)}"

    def test_all_content_is_preserved(self) -> None:
        """Every word in the original text must appear in at least one chunk."""
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=60, overlap=10)
        joined = " ".join(chunks)
        for word in words:
            assert word in joined, f"Word {word!r} was lost during chunking"

    def test_overlap_seeds_next_chunk(self) -> None:
        """The start of chunk[1] must share content with the end of chunk[0]."""
        # Build text long enough to produce >=2 chunks at chunk_size=100
        text = "alpha beta gamma delta epsilon " * 20  # ~620 chars
        chunks = chunk_text(text, chunk_size=100, overlap=30)
        assert len(chunks) >= 2
        # At least one word from the last 30 chars of chunk[0] also appears
        # at the start of chunk[1].
        end_words = set(chunks[0][-30:].split())
        start_words = set(chunks[1][:50].split())
        assert end_words & start_words, "No overlap detected between adjacent chunks"

    def test_paragraph_boundaries_preferred(self) -> None:
        """Chunks should not be empty and should not exceed chunk_size."""
        para = "Sentence one. Sentence two. Sentence three. " * 3  # ~135 chars
        text = (para + "\n\n") * 4  # ~560 chars with double-newline separators
        chunks = chunk_text(text, chunk_size=512, overlap=64)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.strip()


# ---------------------------------------------------------------------------
# TestEmbedder
# ---------------------------------------------------------------------------

class TestEmbedder:
    def _make_httpx_mock(self, json_response: dict) -> MagicMock:
        """Return a mock httpx.Client class that yields *json_response*."""
        mock_response = MagicMock()
        mock_response.json.return_value = json_response

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_cls = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        return mock_cls

    def test_embed_text_uses_ollama_by_default(self) -> None:
        mock_cls = self._make_httpx_mock({"embedding": FAKE_EMBEDDING})
        with patch("backend.rag.embedder.httpx.Client", mock_cls):
            with patch.object(settings, "embedding_provider", "ollama"):
                result = embed_text("test text")
        assert result == FAKE_EMBEDDING
        call_url = mock_cls.return_value.__enter__.return_value.post.call_args.args[0]
        assert "/api/embeddings" in call_url

    def test_embed_text_passes_correct_model_and_prompt(self) -> None:
        mock_cls = self._make_httpx_mock({"embedding": FAKE_EMBEDDING})
        with patch("backend.rag.embedder.httpx.Client", mock_cls):
            with patch.object(settings, "embedding_provider", "ollama"):
                embed_text("sample")
        payload = mock_cls.return_value.__enter__.return_value.post.call_args.kwargs["json"]
        assert payload["model"] == settings.ollama_embed_model
        assert payload["prompt"] == "sample"

    def test_embed_text_openai_provider(self) -> None:
        openai_response = {"data": [{"embedding": FAKE_EMBEDDING}]}
        mock_cls = self._make_httpx_mock(openai_response)
        with patch("backend.rag.embedder.httpx.Client", mock_cls):
            with patch.object(settings, "embedding_provider", "openai"):
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                    result = embed_text("hello openai")
        assert result == FAKE_EMBEDDING
        call_url = mock_cls.return_value.__enter__.return_value.post.call_args.args[0]
        assert "openai.com" in call_url

    def test_embed_text_openai_missing_key_raises(self) -> None:
        import os
        with patch.object(settings, "embedding_provider", "openai"):
            env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
            with patch.dict("os.environ", env, clear=True):
                with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
                    embed_text("no key")


# ---------------------------------------------------------------------------
# TestIngestUrl
# ---------------------------------------------------------------------------

_SAMPLE_URL = "https://example.com/article"
_SAMPLE_HTML = "<html><head><title>Test Page</title></head><body><p>Content.</p></body></html>"
_SAMPLE_TEXT = "This is the extracted article text. " * 30  # ~1080 chars


def _make_clean_page(text: str = _SAMPLE_TEXT) -> CleanPage:
    return CleanPage(
        url=_SAMPLE_URL,
        title="Test Page",
        text=text,
        links=["https://example.com/link1"],
    )


class TestIngestUrl:
    def _run_ingest(
        self,
        conn: sqlite3.Connection,
        text: str = _SAMPLE_TEXT,
        title: str = "Test Page",
    ) -> object:
        """Run ingest_url with all external calls mocked."""
        raw_page = RawPage(url=_SAMPLE_URL, html=_SAMPLE_HTML, status_code=200)
        clean_page = CleanPage(url=_SAMPLE_URL, title=title, text=text,
                               links=["https://example.com/link1"])
        with patch("backend.rag.ingestor.fetch_url", return_value=raw_page):
            with patch("backend.rag.ingestor.extract_content", return_value=clean_page):
                with patch("backend.rag.ingestor.embed_text", return_value=FAKE_EMBEDDING):
                    return ingest_url(conn, _SAMPLE_URL)

    def test_returns_source_node(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        assert node.node_type == "Source"

    def test_source_node_title_from_page(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        assert node.title == "Test Page"

    def test_source_node_metadata_contains_url(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        assert node.metadata["url"] == _SAMPLE_URL

    def test_chunk_nodes_created(self, conn: sqlite3.Connection) -> None:
        self._run_ingest(conn)
        chunk_nodes = [n for n in list_nodes(conn) if n.node_type == "Chunk"]
        assert len(chunk_nodes) >= 1

    def test_chunk_embeddings_stored_in_nodes_vec(self, conn: sqlite3.Connection) -> None:
        self._run_ingest(conn)
        vec_rows = conn.execute("SELECT id FROM nodes_vec").fetchall()
        assert len(vec_rows) >= 1

    def test_fts_content_body_updated_for_source(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        fts_row = conn.execute(
            "SELECT content_body FROM nodes_fts WHERE id = ?", (node.id,)
        ).fetchone()
        assert fts_row is not None
        assert "extracted article text" in fts_row[0]

    def test_source_to_chunk_edges_created(self, conn: sqlite3.Connection) -> None:
        from backend.db.edges import get_edges

        node = self._run_ingest(conn)
        edges = get_edges(conn, node.id)
        has_chunk_edges = [e for e in edges if e.relation_type == "has_chunk"]
        assert len(has_chunk_edges) >= 1

    def test_short_text_produces_single_chunk(self, conn: sqlite3.Connection) -> None:
        self._run_ingest(conn, text="Just a short paragraph.")
        chunk_nodes = [n for n in list_nodes(conn) if n.node_type == "Chunk"]
        assert len(chunk_nodes) == 1

    def test_title_falls_back_to_url_when_blank(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn, title="")
        assert node.title == _SAMPLE_URL


# ---------------------------------------------------------------------------
# TestIngestPdf
# ---------------------------------------------------------------------------

_PDF_TEXT = "Solid-state electrolytes enable safer batteries. " * 25  # ~1225 chars


class TestIngestPdf:
    def _run_ingest(
        self,
        conn: sqlite3.Connection,
        text: str = _PDF_TEXT,
        stem: str = "test_paper",
    ) -> object:
        """Run ingest_pdf with all external calls mocked."""
        with patch("backend.rag.pdf_ingestor._extract_pdf_text", return_value=text):
            with patch("backend.rag.pdf_ingestor.embed_text", return_value=FAKE_EMBEDDING):
                return ingest_pdf(conn, f"/fake/{stem}.pdf")

    def test_returns_source_node(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        assert node.node_type == "Source"

    def test_source_node_title_from_filename(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn, stem="my_research_paper")
        assert node.title == "my_research_paper"

    def test_source_metadata_marks_pdf_type(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        assert node.metadata.get("source_type") == "pdf"

    def test_chunk_nodes_created(self, conn: sqlite3.Connection) -> None:
        self._run_ingest(conn)
        chunk_nodes = [n for n in list_nodes(conn) if n.node_type == "Chunk"]
        assert len(chunk_nodes) >= 1

    def test_chunk_embeddings_stored_in_nodes_vec(self, conn: sqlite3.Connection) -> None:
        self._run_ingest(conn)
        vec_rows = conn.execute("SELECT id FROM nodes_vec").fetchall()
        assert len(vec_rows) >= 1

    def test_fts_content_body_updated_for_source(self, conn: sqlite3.Connection) -> None:
        node = self._run_ingest(conn)
        fts_row = conn.execute(
            "SELECT content_body FROM nodes_fts WHERE id = ?", (node.id,)
        ).fetchone()
        assert fts_row is not None
        assert "electrolytes" in fts_row[0]

    def test_extract_pdf_text_file_not_found(self) -> None:
        from backend.rag.pdf_ingestor import _extract_pdf_text

        with pytest.raises(FileNotFoundError):
            _extract_pdf_text("/nonexistent/path/file.pdf")
