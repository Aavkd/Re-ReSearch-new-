"""Command for visualising and editing the project graph."""

import typer
from backend.db import get_connection, init_db
from backend.db.projects import get_project_nodes, link_to_project
from backend.db.edges import connect_nodes, get_edges
from backend.db.nodes import get_node

from cli.context import load_context, require_context
from cli.rendering import render_tree

map_app = typer.Typer(help="Visualise and connect project nodes.")


@map_app.command("show")
@require_context
def map_show() -> None:
    """Display the project graph as an ASCII tree."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)
        # We need root too
        root = get_node(conn, ctx.active_project_id)
        if not root:
             typer.echo("Project root not found.")
             return
             
        all_nodes = [root] + nodes
        node_ids = {n.id for n in all_nodes}
        
        edges = []
        for n in all_nodes:
            es = get_edges(conn, n.id)
            for e in es:
                if e.target_id in node_ids:
                    edges.append({
                        "source": e.source_id,
                        "target": e.target_id,
                        "relation": e.relation_type
                    })
                    
        # Render
        # Wait, the render_tree logic I wrote expects specific args.
        # Let's verify signature.
        # render_tree(nodes: List[Node], edges: List[Dict], root_id: str)
        
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
    """Create a connection between two nodes."""
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
            
        connect_nodes(conn, source_id, target_id, label)
        typer.echo(f"✅ Connected: {src.title} --[{label}]--> {tgt.title}")
        
    finally:
        conn.close()
