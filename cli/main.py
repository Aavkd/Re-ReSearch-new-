"""Re:Search CLI — domain-oriented entry-point.

Usage:
    python cli/main.py --help

Command groups:
    project   → workspace lifecycle (create, switch, list, status, export)
    library   → ingest sources, search, and recall (RAG Q&A)
    map       → visualise and connect the knowledge graph
    draft     → create and edit artifact documents
    agent     → run the autonomous research agent
    db        → escape hatch: initialise the database
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

import typer

from backend.config import settings
from backend.db import get_connection, init_db

from cli.commands.project import project_app
from cli.commands.library import library_app
from cli.commands.map import map_app
from cli.commands.draft import draft_app
from cli.commands.agent import agent_app

app = typer.Typer(
    name="research",
    help="Re:Search — AI-powered research assistant.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Domain command groups (Phases 8–12)
# ---------------------------------------------------------------------------
app.add_typer(project_app, name="project")
app.add_typer(library_app, name="library")
app.add_typer(map_app, name="map")
app.add_typer(draft_app, name="draft")
app.add_typer(agent_app, name="agent")

# ---------------------------------------------------------------------------
# db init — bootstrapping escape hatch (all other old db commands removed)
# ---------------------------------------------------------------------------
db_app = typer.Typer(help="Database bootstrap operations.", no_args_is_help=True)
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init() -> None:
    """Initialise the SQLite database (create tables if they do not exist)."""
    conn = get_connection()
    init_db(conn)
    conn.close()
    typer.echo(f"[db init] Database ready at {settings.db_path}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app()
