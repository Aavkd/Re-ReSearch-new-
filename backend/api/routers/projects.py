"""Project-scoped REST endpoints.

Routes
------
GET  /projects                     List all Project nodes
POST /projects                     Create a new Project node
GET  /projects/{id}                Project summary (node/edge counts, recent artifacts)
GET  /projects/{id}/nodes          All nodes scoped to this project (BFS depth 2)
GET  /projects/{id}/graph          Subgraph – nodes + edges – for canvas rendering
POST /projects/{id}/link           Link an existing node to this project
GET  /projects/{id}/export         Full subgraph serialised to JSON
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.db.projects import (
    create_project,
    export_project,
    get_project_nodes,
    get_project_summary,
    link_to_project,
    list_projects,
)
from backend.db.edges import get_edges
from backend.db.nodes import get_node

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str


class LinkRequest(BaseModel):
    node_id: str
    relation: str = "HAS_SOURCE"


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _node_dict(node: Any) -> dict[str, Any]:
    return {
        "id": node.id,
        "node_type": node.node_type,
        "title": node.title,
        "content_path": node.content_path,
        "metadata": node.metadata,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


def _edge_dict(edge: Any) -> dict[str, Any]:
    return {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "relation_type": edge.relation_type,
        "created_at": edge.created_at,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[dict[str, Any]])
def list_projects_endpoint(request: Request) -> list[dict[str, Any]]:
    """Return all Project nodes."""
    conn = request.app.state.db
    return [_node_dict(p) for p in list_projects(conn)]


@router.post("", status_code=201, response_model=dict[str, Any])
def create_project_endpoint(body: ProjectCreate, request: Request) -> dict[str, Any]:
    """Create a new Project node and return it."""
    conn = request.app.state.db
    project = create_project(conn, body.name)
    return _node_dict(project)


@router.get("/{project_id}", response_model=dict[str, Any])
def get_project_summary_endpoint(project_id: str, request: Request) -> dict[str, Any]:
    """Return summary stats for a project: node counts by type, recent artifacts."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return get_project_summary(conn, project_id)


@router.get("/{project_id}/nodes", response_model=list[dict[str, Any]])
def get_project_nodes_endpoint(
    project_id: str,
    request: Request,
    depth: int = 2,
) -> list[dict[str, Any]]:
    """Return all nodes reachable from *project_id* within *depth* hops."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    nodes = get_project_nodes(conn, project_id, depth=depth)
    return [_node_dict(n) for n in nodes]


@router.get("/{project_id}/graph", response_model=dict[str, Any])
def get_project_graph_endpoint(
    project_id: str,
    request: Request,
    depth: int = 2,
) -> dict[str, Any]:
    """Return the project subgraph (nodes + edges) for graph-canvas rendering."""
    conn = request.app.state.db
    project_node = get_node(conn, project_id)
    if project_node is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    nodes = get_project_nodes(conn, project_id, depth=depth)
    all_nodes = [project_node] + nodes
    node_ids = {n.id for n in all_nodes}

    seen: set[tuple[str, str, str]] = set()
    edges: list[dict[str, Any]] = []
    for n in all_nodes:
        for e in get_edges(conn, n.id):
            if e.source_id in node_ids and e.target_id in node_ids:
                key = (e.source_id, e.target_id, e.relation_type)
                if key not in seen:
                    seen.add(key)
                    edges.append(_edge_dict(e))

    return {
        "nodes": [_node_dict(n) for n in all_nodes],
        "edges": edges,
    }


@router.post("/{project_id}/link", status_code=201, response_model=dict[str, Any])
def link_node_to_project_endpoint(
    project_id: str,
    body: LinkRequest,
    request: Request,
) -> dict[str, Any]:
    """Link an existing node to this project with the given relation."""
    conn = request.app.state.db
    if get_node(conn, project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    if get_node(conn, body.node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node '{body.node_id}' not found.")
    link_to_project(conn, project_id, body.node_id, body.relation)
    return {"project_id": project_id, "node_id": body.node_id, "relation": body.relation}


@router.get("/{project_id}/export", response_model=dict[str, Any])
def export_project_endpoint(project_id: str, request: Request) -> dict[str, Any]:
    """Serialise the full project subgraph to JSON."""
    conn = request.app.state.db
    try:
        return export_project(conn, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
