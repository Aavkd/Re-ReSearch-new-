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
from fastapi.middleware.cors import CORSMiddleware

from backend.db import get_connection, init_db

from backend.api.routers import nodes as nodes_router
from backend.api.routers import search as search_router
from backend.api.routers import ingest as ingest_router
from backend.api.routers import agent as agent_router
from backend.api.routers import projects as projects_router


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
            "the LangGraph research agent via Server-Sent Events, "
            "and project graph-scoping endpoints."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    # Allow browser frontends on any origin (tighten for production).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(nodes_router.router, prefix="/nodes", tags=["nodes"])
    app.include_router(search_router.router, prefix="/search", tags=["search"])
    app.include_router(ingest_router.router, prefix="/ingest", tags=["ingest"])
    app.include_router(agent_router.router, prefix="/research", tags=["research"])
    app.include_router(projects_router.router, prefix="/projects", tags=["projects"])

    return app


# Module-level instance used by uvicorn:
#   uvicorn backend.api.app:app --reload
app = create_app()
