"""Tests for the 'draft' CLI command group."""

import json
from pathlib import Path
import pytest
import typer
from typer.testing import CliRunner

from backend.db import get_connection, init_db
from backend.db.nodes import create_node
from backend.db.projects import create_project, link_to_project
from cli.context import load_context, save_context, CliContext
from cli.commands.draft import draft_app

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


def test_draft_new(clean_db, monkeypatch):
    # Setup context
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Draft Project")
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    # Mock editor opening to do nothing
    monkeypatch.setattr("cli.commands.draft._open_editor", lambda path: None)
    
    result = runner.invoke(draft_app, ["new", "Chapter 1"])
    assert result.exit_code == 0
    assert "✅ Draft created" in result.stdout
    
    # Verify DB
    conn = get_connection()
    cursor = conn.execute("SELECT title, content_path FROM nodes WHERE node_type='Artifact'")
    row = cursor.fetchone()
    assert row[0] == "Chapter 1"
    assert "content/Chapter_1" in row[1] or "content/" in row[1]
    conn.close()


def test_draft_list(clean_db):
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "List Project")
    
    n1 = create_node(conn, title="Draft A", node_type="Artifact")
    link_to_project(conn, p.id, n1.id, "HAS_ARTIFACT")
    
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    result = runner.invoke(draft_app, ["list"])
    assert result.exit_code == 0
    assert "Draft A" in result.stdout


def test_draft_show(clean_db):
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Show Project")
    
    # Create file
    content_dir = clean_db.parent / "content"
    content_dir.mkdir()
    f = content_dir / "test.md"
    f.write_text("Hello World", encoding="utf-8")
    
    n1 = create_node(conn, title="Draft B", node_type="Artifact", content_path="content/test.md")
    link_to_project(conn, p.id, n1.id, "HAS_ARTIFACT")
    
    conn.close()
    
    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)
    
    result = runner.invoke(draft_app, ["show", n1.id])
    assert result.exit_code == 0
    assert "Hello World" in result.stdout


def test_draft_edit_roundtrip(clean_db, monkeypatch):
    """Editor writes new content; DB content_path is refreshed (updated_at bumped)."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Edit Project")

    # Pre-create a content file so the node already has content_path
    content_dir = clean_db.parent / "content"
    content_dir.mkdir(exist_ok=True)
    content_file = content_dir / "original.md"
    content_file.write_text("Original content", encoding="utf-8")

    n = create_node(conn, title="Edit Me", node_type="Artifact", content_path="content/original.md")
    link_to_project(conn, p.id, n.id, "HAS_ARTIFACT")
    original_ts = conn.execute("SELECT updated_at FROM nodes WHERE id=?", (n.id,)).fetchone()[0]
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    # Mock the editor to write new content into the file it receives
    def mock_editor(path: Path) -> None:
        path.write_text("Edited content", encoding="utf-8")

    monkeypatch.setattr("cli.commands.draft._open_editor", mock_editor)

    import time
    time.sleep(0.01)  # ensure clock advances

    result = runner.invoke(draft_app, ["edit", n.id])
    assert result.exit_code == 0, result.output
    assert "✅ Saved." in result.stdout

    # Verify updated_at was refreshed
    conn = get_connection()
    row = conn.execute("SELECT updated_at, content_path FROM nodes WHERE id=?", (n.id,)).fetchone()
    conn.close()
    assert row["content_path"] is not None


def test_draft_attach(clean_db):
    """draft attach creates a CITES edge from artifact to source."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Attach Project")

    artifact = create_node(conn, title="My Report", node_type="Artifact")
    source = create_node(conn, title="Wikipedia: Foo", node_type="Source")
    link_to_project(conn, p.id, artifact.id, "HAS_ARTIFACT")
    link_to_project(conn, p.id, source.id, "HAS_SOURCE")
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    result = runner.invoke(draft_app, ["attach", artifact.id, source.id])
    assert result.exit_code == 0, result.output
    assert "cites" in result.stdout.lower() or "✅" in result.stdout

    # Verify edge in DB
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM edges WHERE source_id=? AND target_id=? AND relation_type=?",
        (artifact.id, source.id, "CITES"),
    ).fetchone()
    conn.close()
    assert row is not None
