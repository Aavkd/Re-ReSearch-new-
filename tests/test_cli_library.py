"""Tests for the 'library' CLI command group."""

import json
from pathlib import Path
import pytest
import typer
from typer.testing import CliRunner

from backend.db import get_connection, init_db
from backend.db.nodes import create_node
from backend.db.projects import create_project, link_to_project
from cli.context import load_context, save_context, CliContext
from cli.commands.library import library_app

runner = CliRunner()


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Provide a fresh DB and context directory for each test."""
    db_path = tmp_path / "library.db"
    
    monkeypatch.setattr("backend.config.settings.workspace_dir", tmp_path)
    
    cli_dir = tmp_path / ".research_cli"
    cli_dir.mkdir()
    monkeypatch.setattr("cli.context.settings.cli_config_dir", cli_dir)
    
    return db_path


def test_library_list(clean_db):
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Lib Project")
    
    n1 = create_node(conn, title="Source A", node_type="Source")
    link_to_project(conn, p.id, n1.id, "HAS_SOURCE")
    
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    result = runner.invoke(library_app, ["list"])
    assert result.exit_code == 0
    assert "Source A" in result.stdout


def test_library_add_url(clean_db, monkeypatch):
    # Setup context
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Ingest Project")
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    # Mock ingest_url
    def mock_ingest(conn, url):
        return create_node(conn, title="Mock Page", node_type="Source")
        
    monkeypatch.setattr("cli.commands.library.ingest_url", mock_ingest)
    
    result = runner.invoke(library_app, ["add", "https://example.com"])
    assert result.exit_code == 0
    assert "✅ Added source" in result.stdout
    
    # Check linkage
    conn = get_connection()
    nodes = conn.execute(
        """
        SELECT n.title 
        FROM nodes n 
        JOIN edges e ON n.id = e.target_id 
        WHERE e.source_id = ? AND e.relation_type = 'HAS_SOURCE'
        """, 
        (p.id,)
    ).fetchall()
    assert len(nodes) == 1
    assert nodes[0][0] == "Mock Page"
    conn.close()


def test_library_search_scoped(clean_db, monkeypatch):
    # Setup context
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Search Project")
    
    # Node in project
    n1 = create_node(conn, title="In Project", node_type="Source")
    link_to_project(conn, p.id, n1.id, "HAS_SOURCE")
    
    # Node outside project
    n2 = create_node(conn, title="Out Project", node_type="Source")
    
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    # Mock search functions to respect scope
    # Since we can't easily mock FTS/Vec in-memory fully without complex setup,
    # let's mock the backend.db.search.fts_search function.
    
    def mock_fts(conn, query, top_k=10, scope_ids=None):
        # Return n1 if in scope, n2 if global
        results = []
        if not scope_ids or n1.id in scope_ids:
            results.append(n1)
        if not scope_ids or n2.id in scope_ids:
            results.append(n2)
        return results
        
    monkeypatch.setattr("cli.commands.library.fts_search", mock_fts)
    
    # Test scoped search
    result = runner.invoke(library_app, ["search", "query", "--mode", "fuzzy"])
    assert result.exit_code == 0
    assert "In Project" in result.stdout
    assert "Out Project" not in result.stdout
    
    # Test global search
    result = runner.invoke(library_app, ["search", "query", "--mode", "fuzzy", "--global"])
    assert result.exit_code == 0
    assert "In Project" in result.stdout
    assert "Out Project" in result.stdout
