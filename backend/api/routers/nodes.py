"""CRUD endpoints for graph nodes.

Routes
------
POST   /nodes              Create a new node
GET    /nodes              List all nodes (optional ?type= filter)
GET    /nodes/{node_id}    Fetch a single node by UUID
PUT    /nodes/{node_id}    Update node fields
DELETE /nodes/{node_id}    Delete a node (edges cascade)
GET    /nodes/{node_id}/edges  Return all edges for a node
GET    /graph              Return all nodes + edges (graph visualisation)
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from backend.db.edges import get_edges, get_graph_data
from backend.db.nodes import create_node, delete_node, get_node, list_nodes, update_node

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    title: str
    node_type: str
    metadata: Optional[dict[str, Any]] = None
    content_path: Optional[str] = None


class NodeUpdate(BaseModel):
    title: Optional[str] = None
    node_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    content_path: Optional[str] = None


class NodeResponse(BaseModel):
    id: str
    node_type: str
    title: str
    content_path: Optional[str]
    metadata: dict[str, Any]
    created_at: int
    updated_at: int


class EdgeResponse(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    created_at: int


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_response(node) -> dict[str, Any]:  # type: ignore[type-arg]
    return {
        "id": node.id,
        "node_type": node.node_type,
        "title": node.title,
        "content_path": node.content_path,
        "metadata": node.metadata,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=NodeResponse, status_code=201)
def create(body: NodeCreate, request: Request) -> dict[str, Any]:
    """Create a new graph node."""
    conn = request.app.state.db
    node = create_node(
        conn,
        title=body.title,
        node_type=body.node_type,
        metadata=body.metadata,
        content_path=body.content_path,
    )
    return _node_response(node)


@router.get("", response_model=list[NodeResponse])
def list_all(request: Request, type: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all nodes, optionally filtered by ``type``."""
    conn = request.app.state.db
    nodes = list_nodes(conn, node_type=type)
    return [_node_response(n) for n in nodes]




@router.get("/{node_id}", response_model=NodeResponse)
def get_one(node_id: str, request: Request) -> dict[str, Any]:
    """Fetch a single node by its UUID."""
    conn = request.app.state.db
    node = get_node(conn, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id!r}")
    return _node_response(node)


@router.put("/{node_id}", response_model=NodeResponse)
def update(node_id: str, body: NodeUpdate, request: Request) -> dict[str, Any]:
    """Update one or more fields on a node."""
    conn = request.app.state.db
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided to update.")
    try:
        node = update_node(conn, node_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _node_response(node)


@router.delete("/{node_id}")
def remove(node_id: str, request: Request) -> Response:
    """Delete a node and its associated edges (via CASCADE)."""
    conn = request.app.state.db
    delete_node(conn, node_id)
    return Response(status_code=204)


@router.get("/{node_id}/edges", response_model=list[EdgeResponse])
def node_edges(node_id: str, request: Request) -> list[dict[str, Any]]:
    """Return all edges where *node_id* is the source or target."""
    conn = request.app.state.db
    edges = get_edges(conn, node_id)
    return [
        {
            "source_id": e.source_id,
            "target_id": e.target_id,
            "relation_type": e.relation_type,
            "created_at": e.created_at,
        }
        for e in edges
    ]


@router.get("/graph/all", response_model=GraphResponse)
def full_graph(request: Request) -> dict[str, Any]:
    """Return every node and edge for graph visualisation."""
    conn = request.app.state.db
    payload = get_graph_data(conn)
    return {
        "nodes": [_node_response(n) for n in payload.nodes],
        "edges": [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "relation_type": e.relation_type,
                "created_at": e.created_at,
            }
            for e in payload.edges
        ],
    }
