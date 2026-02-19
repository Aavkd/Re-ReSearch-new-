"""Re:Search CLI — entry-point for all backend operations.

Usage:
    python cli/main.py --help

Each sub-command group maps to a backend phase:
    db        → Phase 1 (database layer)
    scrape    → Phase 2 (web scraper)
    ingest    → Phase 3 (RAG ingestion)
    research  → Phase 4 (agent)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (Search/) is on sys.path so that
# `from backend.xxx import ...` works when the CLI is invoked as
# `python cli/main.py` from any working directory.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from typing import Optional

import typer

from backend.config import settings
from backend.db import get_connection, init_db
from backend.db.nodes import create_node, list_nodes
from backend.db.search import fts_search, hybrid_search, vector_search

app = typer.Typer(
    name="research",
    help="Re:Search backend CLI.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Phase 1 — DB commands (stubs, implemented in Phase 1)
# ---------------------------------------------------------------------------
db_app = typer.Typer(help="Database operations.", no_args_is_help=True)
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init() -> None:
    """Initialise the SQLite database (create tables if they do not exist)."""
    conn = get_connection()
    init_db(conn)
    conn.close()
    typer.echo(f"[db init] Database ready at {settings.db_path}")


@db_app.command("create-node")
def db_create_node(
    title: str = typer.Option(..., help="Node title."),
    type: str = typer.Option(..., "--type", help="Node type (e.g. Artifact, Source)."),
) -> None:
    """Create a new node in the database."""
    conn = get_connection()
    init_db(conn)
    node = create_node(conn, title=title, node_type=type)
    conn.close()
    typer.echo(f"[db create-node] Created node: {node.id}  title={node.title!r}  type={node.node_type!r}")


@db_app.command("list-nodes")
def db_list_nodes(
    node_type: Optional[str] = typer.Option(None, "--type", help="Filter by node type."),
) -> None:
    """List all nodes (optionally filtered by type)."""
    conn = get_connection()
    init_db(conn)
    nodes = list_nodes(conn, node_type=node_type)
    conn.close()
    if not nodes:
        typer.echo("[db list-nodes] No nodes found.")
        return
    for n in nodes:
        typer.echo(f"  {n.id}  [{n.node_type}]  {n.title!r}")


@db_app.command("search")
def db_search(
    query: str = typer.Option(..., help="Search query."),
    mode: str = typer.Option("fuzzy", help="Search mode: fuzzy | semantic | hybrid."),
) -> None:
    """Search nodes by keyword, vector similarity, or both."""
    conn = get_connection()
    init_db(conn)

    if mode == "fuzzy":
        results = fts_search(conn, query)
    elif mode == "semantic":
        typer.echo("[db search] Semantic search requires an active embedding model (Phase 3).")
        conn.close()
        raise typer.Exit(1)
    elif mode == "hybrid":
        typer.echo("[db search] Hybrid search requires an active embedding model (Phase 3).")
        conn.close()
        raise typer.Exit(1)
    else:
        typer.echo(f"[db search] Unknown mode {mode!r}. Use: fuzzy | semantic | hybrid")
        conn.close()
        raise typer.Exit(1)

    conn.close()
    if not results:
        typer.echo(f"[db search] No results for {query!r}.")
        return
    for n in results:
        typer.echo(f"  {n.id}  [{n.node_type}]  {n.title!r}")


# ---------------------------------------------------------------------------
# Phase 2 — Scrape commands
# ---------------------------------------------------------------------------
@app.command("scrape")
def scrape(
    url: str = typer.Option(..., help="URL to scrape."),
) -> None:
    """Scrape a URL and print extracted clean text to stdout."""
    from backend.scraper import extract_content, fetch_url

    typer.echo(f"[scrape] Fetching {url!r} …")
    raw = fetch_url(url)
    typer.echo(f"[scrape] HTTP {raw.status_code} — extracting content …")

    clean = extract_content(raw)
    word_count = len(clean.text.split())

    typer.echo(f"[scrape] Title  : {clean.title or '(none)'}")
    typer.echo(f"[scrape] Words  : {word_count}")
    typer.echo(f"[scrape] Links  : {len(clean.links)}")
    typer.echo("")
    typer.echo(clean.text)


# ---------------------------------------------------------------------------
# Phase 3 — Ingest commands (stubs, implemented in Phase 3)
# ---------------------------------------------------------------------------
ingest_app = typer.Typer(help="RAG ingestion operations.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("url")
def ingest_url(
    url: str = typer.Option(..., help="URL to scrape and ingest."),
) -> None:
    """Scrape a URL and ingest it into the knowledge base."""
    typer.echo(f"[ingest url] Not yet implemented — coming in Phase 3. url={url!r}")


@ingest_app.command("pdf")
def ingest_pdf(
    path: str = typer.Option(..., help="Local path to a PDF file."),
) -> None:
    """Ingest a PDF file into the knowledge base."""
    typer.echo(f"[ingest pdf] Not yet implemented — coming in Phase 3. path={path!r}")


# ---------------------------------------------------------------------------
# Phase 4 — Research agent command (stub, implemented in Phase 4)
# ---------------------------------------------------------------------------
@app.command("research")
def research(
    goal: str = typer.Option(..., help="Research goal / question."),
    depth: str = typer.Option("standard", help="Research depth: quick | standard | deep."),
) -> None:
    """Run the autonomous researcher agent against a goal."""
    typer.echo(f"[research] Not yet implemented — coming in Phase 4. goal={goal!r} depth={depth!r}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app()
