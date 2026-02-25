"""Tests for the 'map' CLI command group."""

import pytest
from typer.testing import CliRunner

from backend.db import get_connection, init_db
from backend.db.nodes import create_node
from backend.db.projects import create_project, link_to_project
from cli.context import CliContext, save_context
from cli.commands.map import map_app

runner = CliRunner()


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Provide a fresh DB and context directory for each test."""
    monkeypatch.setattr("backend.config.settings.workspace_dir", tmp_path)

    cli_dir = tmp_path / ".research_cli"
    cli_dir.mkdir()
    monkeypatch.setattr("cli.context.settings.cli_config_dir", cli_dir)

    return tmp_path


def test_map_show_tree(clean_db):
    """map show --format tree outputs the project name and linked child nodes."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Tree Project")

    child = create_node(conn, title="Child Node", node_type="Source")
    link_to_project(conn, p.id, child.id, "HAS_SOURCE")
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    result = runner.invoke(map_app, ["show", "--format", "tree"])
    assert result.exit_code == 0
    assert "Tree Project" in result.stdout
    assert "Child Node" in result.stdout


def test_map_show_list(clean_db):
    """map show --format list outputs a flat list containing all project nodes."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "List Project")

    n1 = create_node(conn, title="Source Alpha", node_type="Source")
    n2 = create_node(conn, title="Source Beta", node_type="Source")
    link_to_project(conn, p.id, n1.id, "HAS_SOURCE")
    link_to_project(conn, p.id, n2.id, "HAS_SOURCE")
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    result = runner.invoke(map_app, ["show", "--format", "list"])
    assert result.exit_code == 0
    assert "Source Alpha" in result.stdout
    assert "Source Beta" in result.stdout


def test_map_connect(clean_db):
    """map connect creates an edge between two nodes in the project."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Connect Project")

    n1 = create_node(conn, title="Node A", node_type="Source")
    n2 = create_node(conn, title="Node B", node_type="Source")
    link_to_project(conn, p.id, n1.id, "HAS_SOURCE")
    link_to_project(conn, p.id, n2.id, "HAS_SOURCE")
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    result = runner.invoke(map_app, ["connect", n1.id, n2.id, "--label", "CITES"])
    assert result.exit_code == 0
    assert "Connected" in result.stdout
    assert "CITES" in result.stdout

    # Verify edge was persisted
    conn = get_connection()
    edge = conn.execute(
        "SELECT * FROM edges WHERE source_id = ? AND target_id = ? AND relation_type = 'CITES'",
        (n1.id, n2.id),
    ).fetchone()
    conn.close()
    assert edge is not None


def test_map_connect_invalid_node(clean_db):
    """map connect refuses to link a node that does not belong to the project."""
    conn = get_connection()
    init_db(conn)
    p = create_project(conn, "Scope Project")

    # n1 is in the project; n2 is NOT
    n1 = create_node(conn, title="In Project", node_type="Source")
    link_to_project(conn, p.id, n1.id, "HAS_SOURCE")

    n2 = create_node(conn, title="Outside Project", node_type="Source")
    # deliberately not linked
    conn.close()

    ctx = CliContext(active_project_id=p.id, active_project_name=p.title)
    save_context(ctx)

    result = runner.invoke(map_app, ["connect", n1.id, n2.id, "--label", "RELATED_TO"])
    assert result.exit_code != 0
    assert "does not belong" in result.stdout
