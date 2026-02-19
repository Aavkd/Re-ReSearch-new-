"""Build and compile the LangGraph research StateGraph.

The graph topology is:

    START → planner → searcher → scraper → synthesiser → evaluator
                ↑                                              |
                └───────────── (if not done) ─────────────────┘
                                                              ↓
                                                             END (if done)

All nodes are created as closures via the ``make_*`` factories in
``backend.agent.nodes``, so every node shares the same DB connection without
it appearing in the serialisable state bag.
"""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.agent.nodes import (
    make_evaluator,
    make_planner,
    make_scraper,
    make_searcher,
    make_synthesiser,
)
from backend.agent.state import ResearchState


def build_graph(conn: sqlite3.Connection):
    """Compile and return the research ``StateGraph``.

    Args:
        conn: Open, initialised DB connection that will be captured by every
            node closure.

    Returns:
        A compiled LangGraph ``CompiledGraph`` with an in-memory checkpointer.
        The checkpointer allows mid-run state inspection and future resumability.
    """
    graph = StateGraph(ResearchState)

    # ------------------------------------------------------------------
    # Register nodes (each is a closure over *conn*)
    # ------------------------------------------------------------------
    graph.add_node("planner", make_planner(conn))
    graph.add_node("searcher", make_searcher(conn))
    graph.add_node("scraper", make_scraper(conn))
    graph.add_node("synthesiser", make_synthesiser(conn))
    graph.add_node("evaluator", make_evaluator(conn))

    # ------------------------------------------------------------------
    # Linear edges
    # ------------------------------------------------------------------
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "scraper")
    graph.add_edge("scraper", "synthesiser")
    graph.add_edge("synthesiser", "evaluator")

    # ------------------------------------------------------------------
    # Conditional edge from evaluator
    # ------------------------------------------------------------------
    def _route_evaluator(state: ResearchState) -> str:
        """Return the next node name (or END) based on the evaluator decision."""
        return END if state["status"] == "done" else "planner"

    graph.add_conditional_edges("evaluator", _route_evaluator)

    # ------------------------------------------------------------------
    # Compile with an in-memory checkpointer for session persistence
    # ------------------------------------------------------------------
    return graph.compile(checkpointer=MemorySaver())
