"""Tests for the 'project' CLI command group."""

import json
from pathlib import Path
import pytest
import typer
from typer.testing import CliRunner

from backend.db import get_connection, init_db
from backend.db.projects import create_project
from cli.context import load_context, save_context, CliContext
from cli.commands.project import project_app

runner = CliRunner()


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Provide a fresh DB and context directory for each test."""
    db_path = tmp_path / "library.db"
    
    # Patch DB path in settings
    # We need to patch where get_connection uses it OR patch get_connection default.
    # get_connection uses settings.db_path.
    monkeypatch.setattr("backend.config.settings.workspace_dir", tmp_path)
    
    # Patch context dir
    cli_dir = tmp_path / ".research_cli"
    cli_dir.mkdir()
    monkeypatch.setattr("cli.context.settings.cli_config_dir", cli_dir)
    
    return db_path


def test_project_new(clean_db):
    result = runner.invoke(project_app, ["new", "Test Project"])
    assert result.exit_code == 0
    assert "✅ Project created" in result.stdout
    
    # Verify context updated
    ctx = load_context()
    assert ctx.active_project_name == "Test Project"
    assert ctx.active_project_id is not None
    
    # Verify DB insertion
    conn = get_connection()
    cursor = conn.execute("SELECT title FROM nodes WHERE node_type='Project'")
    row = cursor.fetchone()
    assert row[0] == "Test Project"
    conn.close()


def test_project_list(clean_db):
    # Pre-populate DB
    conn = get_connection()
    init_db(conn)
    create_project(conn, "P1")
    create_project(conn, "P2")
    conn.close()
    
    result = runner.invoke(project_app, ["list"])
    assert result.exit_code == 0
    assert "P1" in result.stdout
    assert "P2" in result.stdout


def test_project_switch_by_name(clean_db):
    # Create project manually
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Target Project")
    conn.close()
    
    # Switch to it
    result = runner.invoke(project_app, ["switch", "Target Project"])
    assert result.exit_code == 0
    assert "📂 Switched to project" in result.stdout
    
    ctx = load_context()
    assert ctx.active_project_id == p.id


def test_project_status(clean_db):
    # Setup context
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Status Test")
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    result = runner.invoke(project_app, ["status"])
    assert result.exit_code == 0
    assert "Status Test" in result.stdout
    assert "Total Nodes" in result.stdout


def test_project_export(clean_db):
    # Setup context
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Export Test")
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    output_file = Path("export.json")
    if output_file.exists():
        output_file.unlink()
        
    result = runner.invoke(project_app, ["export", "--output", str(output_file)])
    assert result.exit_code == 0
    assert output_file.exists()
    
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["project"]["name"] == "Export Test"
    
    # Cleanup
    output_file.unlink()
