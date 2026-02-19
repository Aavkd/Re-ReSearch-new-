"""Unit tests for Phase 4 — LangGraph researcher agent.

Mocking strategy
----------------
* LLM calls  — ``backend.agent.nodes._get_llm`` returns a ``MagicMock``
  whose ``.invoke()`` returns a fake ``AIMessage``-like object.
* Network     — ``backend.agent.nodes.web_search`` and
  ``backend.agent.tools.web_search`` patched to return URL lists directly.
* DB + ingest — ``backend.agent.nodes.scrape_and_ingest`` and
  ``backend.agent.nodes.rag_retrieve`` patched to return strings; no real
  DB or HTTP connection is required.
"""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.agent.state import ResearchState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_ai_message(content: str) -> SimpleNamespace:
    """Minimal stand-in for a LangChain ``AIMessage``."""
    return SimpleNamespace(content=content)


def _base_state(**overrides) -> ResearchState:
    """Return a minimal ResearchState with all keys present."""
    state: ResearchState = {
        "goal": "What is solid-state battery technology?",
        "plan": [],
        "urls_found": [],
        "urls_scraped": [],
        "findings": [],
        "report": "",
        "iteration": 0,
        "status": "planning",
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


# ---------------------------------------------------------------------------
# state.py — schema verification
# ---------------------------------------------------------------------------

class TestResearchState:
    def test_all_required_keys_present(self):
        state = _base_state()
        for key in (
            "goal", "plan", "urls_found", "urls_scraped",
            "findings", "report", "iteration", "status",
        ):
            assert key in state

    def test_values_have_correct_types(self):
        state = _base_state()
        assert isinstance(state["goal"], str)
        assert isinstance(state["plan"], list)
        assert isinstance(state["urls_found"], list)
        assert isinstance(state["urls_scraped"], list)
        assert isinstance(state["findings"], list)
        assert isinstance(state["report"], str)
        assert isinstance(state["iteration"], int)
        assert isinstance(state["status"], str)


# ---------------------------------------------------------------------------
# tools.py — unit tests
# ---------------------------------------------------------------------------

class TestWebSearch:
    def test_returns_list_of_urls(self):
        fake_results = [{"href": "https://example.com/a"}, {"href": "https://example.com/b"}]
        with patch("backend.agent.tools.DDGS") as mock_ddgs_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(return_value=fake_results)
            mock_ddgs_cls.return_value = ctx

            from backend.agent.tools import web_search
            result = web_search("solid state battery")

        assert result == ["https://example.com/a", "https://example.com/b"]

    def test_filters_results_without_href(self):
        fake_results = [{"href": "https://example.com"}, {"title": "no href"}]
        with patch("backend.agent.tools.DDGS") as mock_ddgs_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(return_value=fake_results)
            mock_ddgs_cls.return_value = ctx

            from backend.agent.tools import web_search
            result = web_search("test")

        assert result == ["https://example.com"]

    def test_returns_empty_list_on_no_results(self):
        with patch("backend.agent.tools.DDGS") as mock_ddgs_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.text = MagicMock(return_value=[])
            mock_ddgs_cls.return_value = ctx

            from backend.agent.tools import web_search
            result = web_search("obscure topic")

        assert result == []


class TestScrapeAndIngest:
    def test_returns_formatted_summary(self):
        fake_node = MagicMock()
        fake_node.title = "Battery Tech Overview"
        fake_node.metadata = {"word_count": 1500}

        with patch("backend.agent.tools.ingest_url", return_value=fake_node):
            from backend.agent.tools import scrape_and_ingest
            result = scrape_and_ingest(MagicMock(), "https://example.com/battery")

        assert "Battery Tech Overview" in result
        assert "1500" in result

    def test_propagates_ingest_exceptions(self):
        with patch("backend.agent.tools.ingest_url", side_effect=RuntimeError("network error")):
            from backend.agent.tools import scrape_and_ingest
            with pytest.raises(RuntimeError, match="network error"):
                scrape_and_ingest(MagicMock(), "https://bad.example.com")


class TestRagRetrieve:
    def test_returns_formatted_chunks(self):
        node_a = MagicMock()
        node_a.node_type = "Chunk"
        node_a.title = "Battery [chunk 1/3]"
        node_a.metadata = {"text": "Solid-state batteries use ceramic electrolytes."}

        with patch("backend.agent.tools.embed_text", return_value=[0.1] * 768), \
             patch("backend.agent.tools.hybrid_search", return_value=[node_a]):
            from backend.agent.tools import rag_retrieve
            result = rag_retrieve(MagicMock(), "electrolyte")

        assert "Chunk" in result
        assert "ceramic electrolytes" in result

    def test_falls_back_to_fts_when_embedder_unavailable(self):
        node_b = MagicMock()
        node_b.node_type = "Chunk"
        node_b.title = "Battery [chunk 2/3]"
        node_b.metadata = {"text": "High energy density."}

        with patch("backend.agent.tools.embed_text", side_effect=ConnectionError("ollama down")), \
             patch("backend.agent.tools.fts_search", return_value=[node_b]):
            from backend.agent.tools import rag_retrieve
            result = rag_retrieve(MagicMock(), "energy density")

        assert "High energy density" in result

    def test_returns_no_results_message_when_empty(self):
        with patch("backend.agent.tools.embed_text", side_effect=ConnectionError()), \
             patch("backend.agent.tools.fts_search", return_value=[]):
            from backend.agent.tools import rag_retrieve
            result = rag_retrieve(MagicMock(), "nothing here")

        assert "No relevant content" in result


# ---------------------------------------------------------------------------
# nodes.py — unit tests via factory functions
# ---------------------------------------------------------------------------

MOCK_CONN = MagicMock(spec=sqlite3.Connection)


class TestPlannerNode:
    def test_extracts_queries_from_llm_response(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message(
            "solid state battery 2024\nbattery electrolyte comparison\nenergy density lithium"
        )

        from backend.agent.nodes import make_planner
        planner = make_planner(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm):
            result = planner(_base_state())

        assert result["plan"] == [
            "solid state battery 2024",
            "battery electrolyte comparison",
            "energy density lithium",
        ]
        assert result["iteration"] == 1
        assert result["status"] == "searching"

    def test_increments_iteration(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message("query one\nquery two")

        from backend.agent.nodes import make_planner
        planner = make_planner(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm):
            result = planner(_base_state(iteration=2))

        assert result["iteration"] == 3

    def test_falls_back_to_goal_on_empty_llm_response(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message("   \n  \n  ")

        from backend.agent.nodes import make_planner
        planner = make_planner(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm):
            result = planner(_base_state(goal="My research goal"))

        assert result["plan"] == ["My research goal"]

    def test_caps_queries_at_three(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message("q1\nq2\nq3\nq4\nq5")

        from backend.agent.nodes import make_planner
        planner = make_planner(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm):
            result = planner(_base_state())

        assert len(result["plan"]) == 3


class TestSearcherNode:
    def test_collects_urls_from_all_queries(self):
        from backend.agent.nodes import make_searcher
        searcher = make_searcher(MOCK_CONN)

        with patch(
            "backend.agent.nodes.web_search",
            side_effect=[
                ["https://a.com", "https://b.com"],
                ["https://c.com"],
            ],
        ):
            result = searcher(_base_state(plan=["query 1", "query 2"]))

        assert result["urls_found"] == ["https://a.com", "https://b.com", "https://c.com"]

    def test_deduplicates_urls(self):
        from backend.agent.nodes import make_searcher
        searcher = make_searcher(MOCK_CONN)

        with patch(
            "backend.agent.nodes.web_search",
            side_effect=[
                ["https://dup.com", "https://unique.com"],
                ["https://dup.com"],
            ],
        ):
            result = searcher(_base_state(plan=["q1", "q2"]))

        assert result["urls_found"].count("https://dup.com") == 1

    def test_continues_when_one_query_fails(self):
        from backend.agent.nodes import make_searcher
        searcher = make_searcher(MOCK_CONN)

        with patch(
            "backend.agent.nodes.web_search",
            side_effect=[RuntimeError("rate limited"), ["https://ok.com"]],
        ):
            result = searcher(_base_state(plan=["q1", "q2"]))

        assert result["urls_found"] == ["https://ok.com"]


class TestScraperNode:
    def test_ingests_urls_and_records_findings(self):
        from backend.agent.nodes import make_scraper
        scraper = make_scraper(MOCK_CONN)

        with patch(
            "backend.agent.nodes.scrape_and_ingest",
            return_value="Ingested: 'Battery Page' (500 words)",
        ):
            result = scraper(_base_state(urls_found=["https://example.com/battery"]))

        assert "https://example.com/battery" in result["urls_scraped"]
        assert any("Battery Page" in f for f in result["findings"])

    def test_respects_max_concurrent_scrapes_limit(self):
        from backend.agent.nodes import make_scraper
        scraper = make_scraper(MOCK_CONN)

        urls = [f"https://example.com/{i}" for i in range(10)]
        call_count = 0

        def fake_ingest(conn, url):
            nonlocal call_count
            call_count += 1
            return f"Ingested: {url!r} (100 words)"

        with patch("backend.agent.nodes.scrape_and_ingest", side_effect=fake_ingest), \
             patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.agent_max_concurrent_scrapes = 3
            scraper(_base_state(urls_found=urls))

        assert call_count == 3

    def test_skips_already_scraped_urls(self):
        from backend.agent.nodes import make_scraper
        scraper = make_scraper(MOCK_CONN)

        with patch(
            "backend.agent.nodes.scrape_and_ingest",
            return_value="Ingested: 'New Page' (200 words)",
        ) as mock_ingest:
            result = scraper(_base_state(
                urls_found=["https://already.com", "https://new.com"],
                urls_scraped=["https://already.com"],
            ))

        mock_ingest.assert_called_once()
        assert "https://new.com" in result["urls_scraped"]
        assert "https://already.com" in result["urls_scraped"]

    def test_continues_on_failed_scrape(self):
        from backend.agent.nodes import make_scraper
        scraper = make_scraper(MOCK_CONN)

        def fake_ingest(conn, url):
            if "bad" in url:
                raise ConnectionError("timeout")
            return f"Ingested: {url!r} (300 words)"

        with patch("backend.agent.nodes.scrape_and_ingest", side_effect=fake_ingest):
            result = scraper(_base_state(urls_found=["https://bad.com", "https://good.com"]))

        assert "https://good.com" in result["urls_scraped"]
        assert "https://bad.com" not in result["urls_scraped"]


class TestSynthesiserNode:
    def test_produces_report_string(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message("# Report\n\nKey findings here.")

        from backend.agent.nodes import make_synthesiser
        synthesiser = make_synthesiser(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm), \
             patch("backend.agent.nodes.rag_retrieve", return_value="chunk text"):
            result = synthesiser(_base_state(findings=["Ingested: 'Page A' (400 words)"]))

        assert "Report" in result["report"]
        assert result["status"] == "evaluating"

    def test_calls_rag_retrieve_with_goal(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _fake_ai_message("Report content")

        from backend.agent.nodes import make_synthesiser
        synthesiser = make_synthesiser(MOCK_CONN)

        with patch("backend.agent.nodes._get_llm", return_value=mock_llm), \
             patch("backend.agent.nodes.rag_retrieve", return_value="retrieved") as mock_retrieve:
            synthesiser(_base_state(goal="Solid-state batteries"))

        mock_retrieve.assert_called_once_with(MOCK_CONN, "Solid-state batteries")


class TestEvaluatorNode:
    def test_done_when_findings_present(self):
        from backend.agent.nodes import make_evaluator
        evaluator = make_evaluator(MOCK_CONN)

        result = evaluator(_base_state(findings=["found something"], iteration=1))
        assert result["status"] == "done"

    def test_re_plans_when_no_findings_and_under_limit(self):
        from backend.agent.nodes import make_evaluator
        evaluator = make_evaluator(MOCK_CONN)

        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.agent_max_iterations = 5
            result = evaluator(_base_state(findings=[], iteration=2))

        assert result["status"] == "re-planning"

    def test_done_when_iteration_limit_reached_without_findings(self):
        from backend.agent.nodes import make_evaluator
        evaluator = make_evaluator(MOCK_CONN)

        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.agent_max_iterations = 3
            result = evaluator(_base_state(findings=[], iteration=3))

        assert result["status"] == "done"


# ---------------------------------------------------------------------------
# graph.py — compilation smoke test
# ---------------------------------------------------------------------------

class TestBuildGraph:
    def test_graph_compiles_without_error(self):
        from backend.agent.graph import build_graph
        compiled = build_graph(MOCK_CONN)
        assert compiled is not None

    def test_graph_has_expected_nodes(self):
        from backend.agent.graph import build_graph
        compiled = build_graph(MOCK_CONN)
        node_names = set(compiled.get_graph().nodes.keys())
        for expected in ("planner", "searcher", "scraper", "synthesiser", "evaluator"):
            assert expected in node_names, f"Missing node: {expected}"
