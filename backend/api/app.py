"""FastAPI application factory.

Lifespan
--------
On startup the app opens a single SQLite connection (shared across all
requests via ``request.app.state.db``) and initialises the schema.  On
shutdown it closes the connection cleanly.

Routers
-------
All endpoint groups are mounted under their respective path prefix:

    /nodes     — CRUD operations on graph nodes
    /search    — FTS / vector / hybrid search
    /ingest    — URL and PDF ingestion
    /research  — Autonomous research agent (SSE streaming)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from backend.db import get_connection, init_db

from backend.api.routers import nodes as nodes_router
from backend.api.routers import search as search_router
from backend.api.routers import ingest as ingest_router
from backend.api.routers import agent as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the DB on startup and close it on shutdown."""
    conn = get_connection()
    init_db(conn)
    app.state.db = conn
    try:
        yield
    finally:
        conn.close()


def create_app() -> FastAPI:
    """Return a fully-configured FastAPI application instance."""
    app = FastAPI(
        title="Re:Search API",
        description=(
            "REST interface for the Re:Search autonomous research backend. "
            "Exposes node CRUD, full-text / vector search, RAG ingestion, "
            "and the LangGraph research agent via Server-Sent Events."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(nodes_router.router, prefix="/nodes", tags=["nodes"])
    app.include_router(search_router.router, prefix="/search", tags=["search"])
    app.include_router(ingest_router.router, prefix="/ingest", tags=["ingest"])
    app.include_router(agent_router.router, prefix="/research", tags=["research"])

    return app


# Module-level instance used by uvicorn:
#   uvicorn backend.api.app:app --reload
app = create_app()
