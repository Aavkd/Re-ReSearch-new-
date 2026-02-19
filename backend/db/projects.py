"""Domain-specific helpers for Project management.

A Project is a Node of type 'Project'.
Project scoping is defined by graph traversal: all nodes reachable from the
Project root node within N hops (default 2) are considered 'in' the project.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.db.edges import connect_nodes, get_edges
from backend.db.nodes import create_node, get_node, list_nodes
from backend.db.models import Node, Edge


def create_project(conn, name: str) -> Node:
    """Create a new Project node."""
    # We use the generic create_node but enforce type="Project"
    return create_node(conn, title=name, node_type="Project")


def list_projects(conn) -> List[Node]:
    """List all nodes of type 'Project'."""
    return list_nodes(conn, node_type="Project")


def link_to_project(conn, project_id: str, node_id: str, relation: str = "HAS_SOURCE") -> None:
    """Connect a node to a project."""
    connect_nodes(conn, project_id, node_id, relation)


def get_project_nodes(conn, project_id: str, depth: int = 2) -> List[Node]:
    """Fetch all nodes belonging to a project via graph traversal.
    
    Uses a recursive Common Table Expression (CTE) to find reachable nodes.
    """
    query = """
    WITH RECURSIVE reachable(id, depth) AS (
        SELECT ?, 0
        UNION ALL
        SELECT e.target_id, r.depth + 1
        FROM edges e 
        JOIN reachable r ON e.source_id = r.id
        WHERE r.depth < ?
    )
    SELECT DISTINCT n.* 
    FROM nodes n 
    JOIN reachable r ON n.id = r.id
    WHERE n.id != ?  -- Exclude the project root itself if desired, but usually we want content
    """
    # Note: We might want to include the project root or not. 
    # Let's include it if depth=0, but the query above excludes it explicitly?
    # Actually, the recursive anchor 'SELECT ?, 0' puts the project_id in reachable.
    # If we want the project node itself, remove the 'WHERE n.id != ?'.
    # Usually for a "list of items in project", we exclude the container.
    # Let's stick to returning *content* nodes. So excluding root is good.
    
    cursor = conn.execute(query, (project_id, depth, project_id))
    rows = cursor.fetchall()
    
    nodes = []
    for row in rows:
        # row is a tuple, but we don't know the exact order of columns in "SELECT *"
        # unless we check the table schema order.
        # Nodes table schema: id, node_type, title, content_path, metadata, created_at, updated_at
        
        # However, to be safe and robust, let's use the same row_factory logic or map by name if cursor has description.
        # sqlite3.Row factory is usually set on the connection.
        
        if isinstance(row, sqlite3.Row):
            # If the connection has row_factory=sqlite3.Row
             nodes.append(Node(
                id=row["id"],
                node_type=row["node_type"],
                title=row["title"],
                content_path=row["content_path"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))
        else:
            # Fallback for raw tuples (id, node_type, title, content_path, metadata, created_at, updated_at)
            # Based on CREATE TABLE order:
            # 0: id
            # 1: node_type
            # 2: title
            # 3: content_path
            # 4: metadata
            # 5: created_at
            # 6: updated_at
            
            # The previous code assumed row[1]=title and row[2]=node_type.
            # But CREATE TABLE has node_type BEFORE title.
            # That explains why "T1" (type) was showing up as title in the failed test.
            
            nodes.append(Node(
                id=row[0],
                node_type=row[1],
                title=row[2],
                content_path=row[3],
                metadata=json.loads(row[4] or "{}"),
                created_at=row[5],
                updated_at=row[6]
            ))
            
    return nodes


def get_project_summary(conn, project_id: str) -> Dict[str, Any]:
    """Get statistics for a project."""
    nodes = get_project_nodes(conn, project_id, depth=2)
    
    summary = {
        "total_nodes": len(nodes),
        "by_type": {},
        "recent_artifacts": []
    }
    
    for n in nodes:
        # Debug print if needed
        # print(f"Processing node {n.id} type={n.node_type}")
        
        # Ensure we're using the correct attribute name from the Node dataclass
        # Node dataclass has 'node_type' field.
        # Check if the node_type is actually populated correctly.
        # The summary dict keys are the values of n.node_type.
        
        # FIX: The test expects "Source" but maybe we are getting something else?
        # Let's inspect what we are putting in.
        summary["by_type"][n.node_type] = summary["by_type"].get(n.node_type, 0) + 1
        
        if n.node_type == "Artifact":
            summary["recent_artifacts"].append(n.title)
            
    # Sort recent artifacts by something? For now just take last 5
    summary["recent_artifacts"] = summary["recent_artifacts"][-5:]
    
    return summary


def export_project(conn, project_id: str) -> Dict[str, Any]:
    """Serialize the project subgraph to a dictionary."""
    project_root = get_node(conn, project_id)
    if not project_root:
        raise ValueError(f"Project {project_id} not found")
        
    nodes = get_project_nodes(conn, project_id, depth=2)
    
    edges_list = []
    # To avoid duplicates, we can track seen edges or use a set of tuples
    seen_edges = set()
    
    # Include root in export for edge discovery
    all_nodes = [project_root] + nodes
    node_ids = {n.id for n in all_nodes}
    
    for n in all_nodes:
        # get_edges returns all connected edges (incoming and outgoing)
        node_edges = get_edges(conn, n.id)
        for e in node_edges:
            # Check if both ends are in our subgraph
            if e.target_id in node_ids and e.source_id in node_ids:
                edge_key = (e.source_id, e.target_id, e.relation_type)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges_list.append({
                        "source": e.source_id,
                        "target": e.target_id,
                        "relation": e.relation_type  
                    })
                
    return {
        "project": {
            "id": project_root.id,
            "name": project_root.title,
            "created_at": project_root.created_at
        },
        "nodes": [
            {
                "id": n.id,
                "type": n.node_type,
                "title": n.title,
                "metadata": n.metadata
            }
            # BUG FIX: The test failure shows title="T1" instead of "N1".
            # Why? Let's check get_project_nodes query.
            # SELECT DISTINCT n.* FROM nodes n ...
            # The row indices: 0=id, 1=title, 2=type...
            # Wait, in get_project_nodes:
            # nodes.append(Node(id=row[0], title=row[1], node_type=row[2], ...))
            
            # If the test is failing with "T1" (which is the type) being the title,
            # then title and type columns might be swapped in the SELECT or Node construction.
            # Let's check schema.sql or model definition.
            # Node dataclass: id, node_type, title ...
            # SELECT * FROM nodes -> order depends on CREATE TABLE.
            
            for n in nodes
        ],
        "edges": edges_list
    }
