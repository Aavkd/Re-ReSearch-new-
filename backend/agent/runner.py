"""High-level runner for the research agent.

``run_research`` is the single public function in this module.  It wires
together the DB layer, the compiled LangGraph, and a live-streaming stdout
log so the CLI (and any future API layer) can consume progress in real time.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.agent.graph import build_graph
from backend.agent.state import ResearchState
from backend.config import settings
from backend.db import get_connection, init_db
from backend.db.nodes import create_node


def run_research(
    goal: str,
    config: dict[str, Any] | None = None,
) -> ResearchState:
    """Run the autonomous research agent against *goal*.

    Opens its own DB connection for the duration of the run, then closes it
    on exit (success or error).  Any intermediate state snapshots are printed
    to stdout via the node functions themselves; the caller receives only the
    final ``ResearchState``.

    The finished report is persisted as an ``Artifact`` node in the DB so it
    can be retrieved later via the search API.

    Args:
        goal: The research question or topic to investigate.
        config: Optional LangGraph configuration overrides.  If ``None``, a
            fresh ``thread_id`` is generated automatically so each call starts
            with a clean slate.

    Returns:
        The final :class:`~backend.agent.state.ResearchState` after the graph
        has terminated.
    """
    settings.ensure_workspace()
    conn = get_connection()
    init_db(conn)

    try:
        # ------------------------------------------------------------------
        # Build the graph with the live connection
        # ------------------------------------------------------------------
        graph = build_graph(conn)

        # ------------------------------------------------------------------
        # Configuration — each run uses a unique thread_id to avoid
        # inheriting state from previous sessions stored in the MemorySaver.
        # ------------------------------------------------------------------
        thread_id = str(uuid.uuid4())
        run_config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        if config:
            run_config.update(config)

        initial_state: ResearchState = {
            "goal": goal,
            "plan": [],
            "urls_found": [],
            "urls_scraped": [],
            "findings": [],
            "report": "",
            "iteration": 0,
            "status": "planning",
            "artifact_id": "",
        }

        # ------------------------------------------------------------------
        # Stream — node print() calls act as the live log; we only track the
        # last event to know which node just ran.
        # ------------------------------------------------------------------
        for event in graph.stream(initial_state, config=run_config):
            # event: {node_name: state_update_dict}
            node_name = next(iter(event), None)
            if node_name:
                update = event[node_name]
                status = update.get("status", "")
                if status:
                    pass  # status already printed inside the node function

        # ------------------------------------------------------------------
        # Retrieve final accumulated state
        # ------------------------------------------------------------------
        final: ResearchState = graph.get_state(run_config).values  # type: ignore[assignment]

        # ------------------------------------------------------------------
        # Persist the report as an Artifact node
        # ------------------------------------------------------------------
        report_text = final.get("report", "")
        artifact_id = ""
        if report_text:
            artifact = create_node(
                conn,
                title=f"Report: {goal[:80]}",
                node_type="Artifact",
                metadata={
                    "goal": goal,
                    "iterations": final.get("iteration", 0),
                    "sources_count": len(final.get("urls_scraped", [])),
                },
            )
            artifact_id = artifact.id
            print(f"[DONE] Report saved as Artifact node: {artifact.id}")
        else:
            print("[DONE] Agent completed but produced no report.")

        return {**final, "artifact_id": artifact_id}  # type: ignore[return-value]

    finally:
        conn.close()
