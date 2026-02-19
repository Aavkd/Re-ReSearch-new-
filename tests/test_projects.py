"""Tests for the project management functions."""

import json
import pytest
from uuid import uuid4

from backend.db import get_connection, init_db
from backend.db.nodes import create_node
from backend.db.edges import connect_nodes
from backend.db.projects import (
    create_project,
    list_projects,
    link_to_project,
    get_project_nodes,
    get_project_summary,
    export_project,
)


@pytest.fixture
def db_conn():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def test_create_project(db_conn):
    proj = create_project(db_conn, "Paris Project")
    assert proj.title == "Paris Project"
    assert proj.node_type == "Project"
    
    # Check it's in list
    projs = list_projects(db_conn)
    assert len(projs) == 1
    assert projs[0].id == proj.id


def test_list_projects_empty(db_conn):
    projs = list_projects(db_conn)
    assert len(projs) == 0


def test_get_project_nodes_depth_1(db_conn):
    proj = create_project(db_conn, "Project A")
    
    # Create some content nodes
    n1 = create_node(db_conn, title="Source 1", node_type="Source")
    n2 = create_node(db_conn, title="Source 2", node_type="Source")
    
    # Link them to the project
    link_to_project(db_conn, proj.id, n1.id, "HAS_SOURCE")
    link_to_project(db_conn, proj.id, n2.id, "HAS_SOURCE")
    
    # Check they are retrieved
    nodes = get_project_nodes(db_conn, proj.id, depth=1)
    node_ids = {n.id for n in nodes}
    
    assert len(nodes) == 2
    assert n1.id in node_ids
    assert n2.id in node_ids
    assert proj.id not in node_ids  # Default excludes root


def test_get_project_nodes_depth_2(db_conn):
    proj = create_project(db_conn, "Project B")
    
    # Structure: Project -> Source 1 -> Artifact 1
    src1 = create_node(db_conn, title="Source 1", node_type="Source")
    art1 = create_node(db_conn, title="Artifact 1", node_type="Artifact")
    
    link_to_project(db_conn, proj.id, src1.id, "HAS_SOURCE")
    connect_nodes(db_conn, src1.id, art1.id, "CITES")
    
    # Check with depth 1 (should miss Artifact)
    d1 = get_project_nodes(db_conn, proj.id, depth=1)
    assert len(d1) == 1
    assert d1[0].id == src1.id
    
    # Check with depth 2 (should catch Artifact)
    d2 = get_project_nodes(db_conn, proj.id, depth=2)
    assert len(d2) == 2
    ids = {n.id for n in d2}
    assert src1.id in ids
    assert art1.id in ids


def test_get_project_nodes_no_cycle(db_conn):
    proj = create_project(db_conn, "Cyclic Project")
    
    # Create a cycle: Project -> A -> B -> A
    a = create_node(db_conn, title="Node A", node_type="Data")
    b = create_node(db_conn, title="Node B", node_type="Data")
    
    link_to_project(db_conn, proj.id, a.id, "HAS_A")
    connect_nodes(db_conn, a.id, b.id, "LINKS_TO")
    connect_nodes(db_conn, b.id, a.id, "LINKS_BACK")
    
    # Should terminate and return distinct nodes
    nodes = get_project_nodes(db_conn, proj.id, depth=5)
    assert len(nodes) == 2
    ids = {n.id for n in nodes}
    assert a.id in ids
    assert b.id in ids


def test_get_project_summary(db_conn):
    proj = create_project(db_conn, "Summary Test")
    
    # Add 2 Sources, 1 Artifact
    for i in range(2):
        n = create_node(db_conn, title=f"Source {i}", node_type="Source")
        link_to_project(db_conn, proj.id, n.id, "HAS_SOURCE")
        
    art = create_node(db_conn, title="My Report", node_type="Artifact")
    link_to_project(db_conn, proj.id, art.id, "HAS_ARTIFACT")
    
    summary = get_project_summary(db_conn, proj.id)
    
    assert summary["total_nodes"] == 3
    assert summary["by_type"]["Source"] == 2
    assert summary["by_type"]["Artifact"] == 1
    assert "My Report" in summary["recent_artifacts"]


def test_export_project(db_conn):
    proj = create_project(db_conn, "Export Me")
    
    n1 = create_node(db_conn, title="N1", node_type="T1")
    link_to_project(db_conn, proj.id, n1.id, "LINK")
    
    exp = export_project(db_conn, proj.id)
    
    assert exp["project"]["name"] == "Export Me"
    assert len(exp["nodes"]) == 1
    assert exp["nodes"][0]["title"] == "N1"
    assert len(exp["edges"]) == 1
    assert exp["edges"][0]["source"] == proj.id
    assert exp["edges"][0]["target"] == n1.id
