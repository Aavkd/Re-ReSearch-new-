"""Command for visualising and editing the project graph."""

from typing import Any

import typer
from backend.config import settings
from backend.db import get_connection, init_db
from backend.db.projects import get_project_nodes, link_to_project
from backend.db.edges import connect_nodes, get_edges
from backend.db.nodes import get_node

from cli.context import load_context, require_context
from cli.rendering import render_tree

map_app = typer.Typer(help="Visualise and connect project nodes.")


def _get_llm() -> Any:
    """Return a configured LangChain chat model based on ``settings``."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_chat_model, temperature=0)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_chat_model, temperature=0)


@map_app.command("show")
@require_context
def map_show(
    format: str = typer.Option("tree", "--format", help="Output format: tree | list"),
) -> None:
    """Display the project graph as an ASCII tree or flat list."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)

    try:
        nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)
        root = get_node(conn, ctx.active_project_id)
        if not root:
            typer.echo("Project root not found.")
            return

        if format == "list":
            typer.echo(f"Nodes in project '{root.title}':")
            typer.echo(f"  [{root.node_type}] {root.title} ({root.id[:8]}...)")
            for n in nodes:
                typer.echo(f"  [{n.node_type}] {n.title} ({n.id[:8]}...)")
            return

        # --- tree format (default) ---
        all_nodes = [root] + nodes
        node_ids = {n.id for n in all_nodes}

        edges = []
        for n in all_nodes:
            for e in get_edges(conn, n.id):
                if e.target_id in node_ids:
                    edges.append({
                        "source": e.source_id,
                        "target": e.target_id,
                        "relation": e.relation_type,
                    })

        tree = render_tree(all_nodes, edges, root.id)
        typer.echo(tree)

    finally:
        conn.close()


@map_app.command("connect")
@require_context
def map_connect(
    source_id: str = typer.Argument(..., help="Source Node ID"),
    target_id: str = typer.Argument(..., help="Target Node ID"),
    label: str = typer.Option("related", help="Relationship type (e.g. CITES, CONTRADICTS)."),
) -> None:
    """Create a connection between two nodes in the active project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)

    try:
        # Validate existence
        src = get_node(conn, source_id)
        tgt = get_node(conn, target_id)

        if not src:
            typer.echo(f"❌ Source {source_id} not found.")
            raise typer.Exit(code=1)
        if not tgt:
            typer.echo(f"❌ Target {target_id} not found.")
            raise typer.Exit(code=1)

        # Validate both nodes belong to the active project
        project_nodes = get_project_nodes(conn, ctx.active_project_id, depth=3)
        project_ids = {n.id for n in project_nodes} | {ctx.active_project_id}

        if source_id not in project_ids:
            typer.echo(f"❌ Source node {source_id} does not belong to the active project.")
            raise typer.Exit(code=1)
        if target_id not in project_ids:
            typer.echo(f"❌ Target node {target_id} does not belong to the active project.")
            raise typer.Exit(code=1)
            
        connect_nodes(conn, source_id, target_id, label)
        typer.echo(f"✅ Connected: {src.title} --[{label}]--> {tgt.title}")

    finally:
        conn.close()


@map_app.command("cluster")
@require_context
def map_cluster(
    apply: bool = typer.Option(False, "--apply", help="Automatically create the proposed edges."),
) -> None:
    """Use the LLM to suggest thematic clusters among project nodes.

    The LLM receives all node titles and summaries from the active project and
    proposes new edges that group related nodes into themes.  Proposed edges
    are printed for review.  Pass ``--apply`` to create them immediately.
    """
    ctx = load_context()
    conn = get_connection()
    init_db(conn)

    try:
        nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)

        if not nodes:
            typer.echo("⚠️  Project has no nodes to cluster.")
            return

        # Build a compact summary for the LLM prompt.
        node_lines = "\n".join(
            f"- id={n.id[:8]} type={n.node_type} title={n.title!r}"
            for n in nodes
        )

        prompt = (
            "You are a research assistant helping organise a knowledge graph.\n"
            "Below is a list of nodes from a project. Each node has a short ID, "
            "a type, and a title.\n\n"
            f"{node_lines}\n\n"
            "Suggest up to 5 thematic connections between these nodes. "
            "For each suggestion output exactly one line in this format:\n"
            "  CONNECT <id_a> <id_b> <RELATION_LABEL>\n"
            "Use only the 8-character IDs shown above. "
            "Choose RELATION_LABEL from: RELATED_TO, SUPPORTS, CONTRADICTS, CITES, EXTENDS.\n"
            "Output ONLY the CONNECT lines, no other text."
        )

        typer.echo("🤔 Asking LLM to suggest clusters…")
        llm = _get_llm()
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)

        # Parse suggestions.
        id_map = {n.id[:8]: n for n in nodes}
        proposals: list[tuple[str, str, str]] = []

        for line in raw.splitlines():
            parts = line.strip().split()
            if len(parts) == 4 and parts[0].upper() == "CONNECT":
                short_a, short_b, relation = parts[1], parts[2], parts[3]
                node_a = id_map.get(short_a)
                node_b = id_map.get(short_b)
                if node_a and node_b:
                    proposals.append((node_a.id, node_b.id, relation))

        if not proposals:
            typer.echo("No valid cluster proposals returned by the LLM.")
            typer.echo(f"Raw response:\n{raw}")
            return

        typer.echo(f"\nProposed connections ({len(proposals)}):")
        for full_a, full_b, rel in proposals:
            na = id_map.get(full_a[:8])
            nb = id_map.get(full_b[:8])
            title_a = na.title if na else full_a[:8]
            title_b = nb.title if nb else full_b[:8]
            typer.echo(f"  {title_a!r} --[{rel}]--> {title_b!r}")

        if apply:
            for full_a, full_b, rel in proposals:
                connect_nodes(conn, full_a, full_b, rel)
            typer.echo(f"\n✅ Applied {len(proposals)} connection(s).")
        else:
            typer.echo("\nRun with --apply to create these edges.")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(code=1)
    finally:
        conn.close()
