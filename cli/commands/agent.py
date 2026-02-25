"""Agent commands for delegated research tied to the active project."""

from __future__ import annotations

from datetime import datetime

import typer

from backend.agent.runner import run_research
from backend.db import get_connection, init_db
from backend.db.nodes import list_nodes
from backend.db.projects import get_project_nodes, link_to_project
from cli.context import load_context, require_context

agent_app = typer.Typer(help="Run the autonomous research agent.")


@agent_app.command("hire")
@require_context
def agent_hire(
    goal: str = typer.Option(..., "--goal", help="Research objective / question."),
    depth: str = typer.Option(
        "standard",
        "--depth",
        help="Research depth: quick | standard | deep (reserved for future use).",
    ),
) -> None:
    """Run the research agent and link its outputs to the active project."""
    ctx = load_context()
    project_id = ctx.active_project_id  # guaranteed non-None by @require_context

    typer.echo(f"🔍 Starting research: {goal!r}  [depth={depth}]")

    # run_research opens its own DB connection internally and closes it on exit.
    state = run_research(goal)

    artifact_id: str = state.get("artifact_id", "")
    urls_scraped: list[str] = state.get("urls_scraped", [])

    # Open a connection to perform the project-linking steps.
    conn = get_connection()
    init_db(conn)
    try:
        # Link the generated report artifact to the project.
        if artifact_id:
            link_to_project(conn, project_id, artifact_id, "HAS_ARTIFACT")
            typer.echo(f"✅ Report linked to project  [{artifact_id[:8]}…]")
        else:
            typer.echo("⚠️  Agent produced no report — nothing to link.")

        # Link every Source node whose URL was scraped during this run.
        if urls_scraped:
            scraped_set = set(urls_scraped)
            source_nodes = list_nodes(conn, node_type="Source")
            linked = 0
            for node in source_nodes:
                if node.metadata.get("url") in scraped_set:
                    link_to_project(conn, project_id, node.id, "HAS_SOURCE")
                    linked += 1
            if linked:
                typer.echo(f"🔗 Linked {linked} source node(s) to project.")

        typer.echo(
            f"\n--- Research complete ---\n"
            f"  Artifact : {artifact_id or 'none'}\n"
            f"  Sources  : {len(urls_scraped)}"
        )
    finally:
        conn.close()


@agent_app.command("status")
@require_context
def agent_status() -> None:
    """List agent-produced research reports in the active project."""
    ctx = load_context()
    project_id = ctx.active_project_id  # guaranteed non-None by @require_context

    conn = get_connection()
    init_db(conn)
    try:
        project_nodes = get_project_nodes(conn, project_id, depth=2)

        # Keep only Artifact nodes that carry a "goal" metadata key
        # (set by runner.py — agent-produced reports only).
        reports = [
            n for n in project_nodes
            if n.node_type == "Artifact" and n.metadata.get("goal")
        ]

        if not reports:
            typer.echo("No agent-produced reports found for this project.")
            return

        typer.echo(f"Agent reports for project '{ctx.active_project_name}':\n")
        for report in reports:
            goal_text = report.metadata.get("goal", "")
            sources = report.metadata.get("sources_count", 0)
            iterations = report.metadata.get("iterations", 0)
            created = datetime.fromtimestamp(report.created_at).strftime("%Y-%m-%d %H:%M")
            typer.echo(f"  [{report.id[:8]}…]  {report.title}")
            typer.echo(f"    Goal      : {goal_text}")
            typer.echo(f"    Sources   : {sources}   Iterations: {iterations}")
            typer.echo(f"    Created   : {created}")
            typer.echo()
    finally:
        conn.close()
