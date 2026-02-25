"""Tests for the 'agent' CLI command group (Phase 12)."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from backend.db import get_connection, init_db
from backend.db.nodes import create_node
from backend.db.projects import create_project, link_to_project, get_project_nodes
from cli.context import CliContext, save_context
from cli.commands.agent import agent_app

runner = CliRunner()


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Fresh DB and context directory isolated per test."""
    monkeypatch.setattr("backend.config.settings.workspace_dir", tmp_path)

    cli_dir = tmp_path / ".research_cli"
    cli_dir.mkdir()
    monkeypatch.setattr("cli.context.settings.cli_config_dir", cli_dir)

    return tmp_path


def test_agent_hire(clean_db):
    """Research runs (mocked), report and sources are linked to the active project."""
    conn = get_connection()
    init_db(conn)

    # Create a project and set it as active.
    project = create_project(conn, "Hire Test Project")

    # Pre-create the artifact and source nodes that the mock runner would have created.
    artifact = create_node(conn, title="Report: test goal", node_type="Artifact",
                           metadata={"goal": "test goal", "iterations": 1, "sources_count": 1})
    source = create_node(conn, title="Test Source", node_type="Source",
                         metadata={"url": "https://example.com/test", "word_count": 100})
    conn.close()

    ctx = CliContext(active_project_id=project.id, active_project_name=project.title)
    save_context(ctx)

    # Fake state returned by run_research.
    fake_state = {
        "goal": "test goal",
        "plan": [],
        "urls_found": ["https://example.com/test"],
        "urls_scraped": ["https://example.com/test"],
        "findings": ["Found something."],
        "report": "The report content.",
        "iteration": 1,
        "status": "done",
        "artifact_id": artifact.id,
    }

    with patch("cli.commands.agent.run_research", return_value=fake_state):
        result = runner.invoke(agent_app, ["hire", "--goal", "test goal"])

    assert result.exit_code == 0, result.output
    assert "Research complete" in result.output
    assert "Report linked to project" in result.output
    assert "1 source node" in result.output

    # Verify DB: both nodes linked to project.
    conn = get_connection()
    project_node_ids = {n.id for n in get_project_nodes(conn, project.id, depth=2)}
    conn.close()

    assert artifact.id in project_node_ids, "Artifact not linked to project"
    assert source.id in project_node_ids, "Source not linked to project"


def test_agent_hire_no_report(clean_db):
    """Command handles gracefully when the agent produces no report."""
    conn = get_connection()
    init_db(conn)
    project = create_project(conn, "No Report Project")
    conn.close()

    ctx = CliContext(active_project_id=project.id, active_project_name=project.title)
    save_context(ctx)

    fake_state = {
        "goal": "empty run",
        "plan": [],
        "urls_found": [],
        "urls_scraped": [],
        "findings": [],
        "report": "",
        "iteration": 1,
        "status": "done",
        "artifact_id": "",
    }

    with patch("cli.commands.agent.run_research", return_value=fake_state):
        result = runner.invoke(agent_app, ["hire", "--goal", "empty run"])

    assert result.exit_code == 0, result.output
    assert "no report" in result.output.lower()


def test_agent_status(clean_db):
    """Lists agent-produced artifacts in the active project."""
    conn = get_connection()
    init_db(conn)

    project = create_project(conn, "Status Test Project")

    # Create an agent-produced artifact (has 'goal' in metadata).
    report = create_node(
        conn,
        title="Report: batteries",
        node_type="Artifact",
        metadata={"goal": "Summarise battery tech", "iterations": 2, "sources_count": 3},
    )
    link_to_project(conn, project.id, report.id, "HAS_ARTIFACT")

    # Create a regular artifact without 'goal' — should not appear.
    draft = create_node(conn, title="Manual Draft", node_type="Artifact", metadata={})
    link_to_project(conn, project.id, draft.id, "HAS_ARTIFACT")

    conn.close()

    ctx = CliContext(active_project_id=project.id, active_project_name=project.title)
    save_context(ctx)

    result = runner.invoke(agent_app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Report: batteries" in result.output
    assert "Summarise battery tech" in result.output
    # The non-agent draft must not be listed.
    assert "Manual Draft" not in result.output


def test_agent_status_no_reports(clean_db):
    """Status command shows a clear message when no reports exist."""
    conn = get_connection()
    init_db(conn)
    project = create_project(conn, "Empty Project")
    conn.close()

    ctx = CliContext(active_project_id=project.id, active_project_name=project.title)
    save_context(ctx)

    result = runner.invoke(agent_app, ["status"])

    assert result.exit_code == 0, result.output
    assert "No agent-produced reports" in result.output


def test_agent_hire_requires_context(clean_db):
    """hire aborts with a clear message when no project is active."""
    # No context set — active_project_id is None.
    result = runner.invoke(agent_app, ["hire", "--goal", "orphan run"])
    assert result.exit_code != 0
    assert "No active project" in result.output
