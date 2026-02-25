"""Library commands for managing sources and recalling information."""

import typer
from pathlib import Path

from backend.db import get_connection, init_db
from backend.db.projects import link_to_project, get_project_nodes
from backend.db.search import hybrid_search, fts_search, vector_search
from backend.rag.ingestor import ingest_url
from backend.rag.pdf_ingestor import ingest_pdf
from backend.rag.embedder import embed_text
from backend.rag.recall import recall as rag_recall

from cli.context import load_context, require_context

library_app = typer.Typer(help="Manage sources and search the knowledge base.")


@library_app.command("add")
@require_context
def library_add(
    target: str = typer.Argument(..., help="URL or file path to ingest."),
) -> None:
    """Add a source to the active project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        if target.startswith("http"):
            typer.echo(f"🌐 Ingesting URL: {target}")
            node = ingest_url(conn, target)
        elif Path(target).exists():
            typer.echo(f"📄 Ingesting File: {target}")
            if target.lower().endswith(".pdf"):
                node = ingest_pdf(conn, target)
            else:
                typer.echo("❌ Only PDF files are supported for now.")
                raise typer.Exit(code=1)
        else:
            typer.echo(f"❌ Invalid target: {target}")
            raise typer.Exit(code=1)
            
        # Link to active project
        link_to_project(conn, ctx.active_project_id, node.id, relation="HAS_SOURCE")
        typer.echo(f"✅ Added source: {node.title} [{node.id}]")
        
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(code=1)
    finally:
        conn.close()


@library_app.command("list")
@require_context
def library_list(
    type: str = typer.Option(None, "--type", help="Filter by node type (Source, Artifact, etc)."),
) -> None:
    """List sources and nodes in the active project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)
        
        if type:
            nodes = [n for n in nodes if n.node_type.lower() == type.lower()]
            
        if not nodes:
            typer.echo("No nodes found.")
            return
            
        typer.echo(f"Library content for {ctx.active_project_name}:")
        for n in nodes:
            typer.echo(f" - [{n.node_type}] {n.title} ({n.id[:8]}...)")
            
    finally:
        conn.close()


@library_app.command("search")
@require_context
def library_search(
    query: str = typer.Argument(..., help="Search query."),
    mode: str = typer.Option("hybrid", help="Search mode: fuzzy | semantic | hybrid"),
    global_: bool = typer.Option(False, "--global", help="Search across ALL projects (ignore context)."),
) -> None:
    """Search for information within the project (or globally)."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        # Determine scope
        scope_ids = None
        if not global_:
            project_nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)
            scope_ids = [n.id for n in project_nodes]
            if not scope_ids:
                typer.echo("⚠️ Project is empty. Nothing to search.")
                return

        typer.echo(f"🔍 Searching for '{query}' ({mode})...")
        
        results = []
        if mode == "fuzzy":
            # Note: fts_search needs update to support scope_ids
            # We will patch backend/db/search.py next.
            results = fts_search(conn, query, top_k=10, scope_ids=scope_ids)
        elif mode == "semantic":
            vec = embed_text(query)
            results = vector_search(conn, vec, top_k=10, scope_ids=scope_ids)
        elif mode == "hybrid":
            vec = embed_text(query)
            results = hybrid_search(conn, query, vec, top_k=10, scope_ids=scope_ids)
            
        if not results:
            typer.echo("No results found.")
            return
            
        for n in results:
            typer.echo(f" - [{n.node_type}] {n.title}")
            
    finally:
        conn.close()


@library_app.command("recall")
@require_context
def library_recall(
    question: str = typer.Argument(..., help="Natural-language question to answer."),
    top_k: int = typer.Option(5, "--top-k", help="Number of chunks to retrieve."),
) -> None:
    """Answer a question using the project's knowledge base (RAG)."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)

    try:
        typer.echo(f"🤔 Recalling: {question!r} …")
        answer = rag_recall(conn, question, project_id=ctx.active_project_id, top_k=top_k)
        typer.echo(answer)
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(code=1)
    finally:
        conn.close()
