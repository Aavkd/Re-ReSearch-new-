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

import typer

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
    typer.echo("[db init] Not yet implemented — coming in Phase 1.")


@db_app.command("create-node")
def db_create_node(
    title: str = typer.Option(..., help="Node title."),
    type: str = typer.Option(..., "--type", help="Node type (e.g. Artifact, Source)."),
) -> None:
    """Create a new node in the database."""
    typer.echo(f"[db create-node] Not yet implemented — coming in Phase 1. title={title!r} type={type!r}")


@db_app.command("list-nodes")
def db_list_nodes(
    node_type: str | None = typer.Option(None, "--type", help="Filter by node type."),
) -> None:
    """List all nodes (optionally filtered by type)."""
    typer.echo(f"[db list-nodes] Not yet implemented — coming in Phase 1. type={node_type!r}")


@db_app.command("search")
def db_search(
    query: str = typer.Option(..., help="Search query."),
    mode: str = typer.Option("fuzzy", help="Search mode: fuzzy | semantic | hybrid."),
) -> None:
    """Search nodes by keyword, vector similarity, or both."""
    typer.echo(f"[db search] Not yet implemented — coming in Phase 1. query={query!r} mode={mode!r}")


# ---------------------------------------------------------------------------
# Phase 2 — Scrape commands (stubs, implemented in Phase 2)
# ---------------------------------------------------------------------------
@app.command("scrape")
def scrape(
    url: str = typer.Option(..., help="URL to scrape."),
) -> None:
    """Scrape a URL and print extracted clean text."""
    typer.echo(f"[scrape] Not yet implemented — coming in Phase 2. url={url!r}")


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
