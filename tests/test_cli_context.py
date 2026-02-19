"""Tests for the CLI context management module."""

import json
from pathlib import Path
from dataclasses import asdict

import pytest
import typer
from typer.testing import CliRunner

from backend.config import settings
from cli.context import (
    CliContext,
    load_context,
    save_context,
    require_context,
    _get_context_path,
)

runner = CliRunner()


@pytest.fixture
def temp_context_dir(tmp_path, monkeypatch):
    """Override the config directory to use a temporary path."""
    context_dir = tmp_path / ".research_cli"
    context_dir.mkdir()
    
    # Patch the _get_context_path function to return our temp file
    # We need to patch where it is IMPORTED in the test file (cli.context)
    def mock_get_context_path():
        return context_dir / "context.json"
    
    monkeypatch.setattr("cli.context.settings.cli_config_dir", context_dir)
    
    return context_dir


def test_load_default_context(temp_context_dir, monkeypatch):
    """Should return defaults when no file exists."""
    # We must patch load_context's internal call to settings or _get_context_path
    monkeypatch.setattr("cli.context.settings.cli_config_dir", temp_context_dir)
    
    ctx = load_context()
    assert isinstance(ctx, CliContext)
    assert ctx.active_project_id is None
    assert ctx.active_project_name is None
    assert ctx.user_preferences == {}


def test_save_and_load_roundtrip(temp_context_dir, monkeypatch):
    """Should save context to disk and load it back correctly."""
    monkeypatch.setattr("cli.context.settings.cli_config_dir", temp_context_dir)

    ctx = CliContext(
        active_project_id="uuid-1234",
        active_project_name="Test Project",
        user_preferences={"editor": "vim"}
    )
    
    save_context(ctx)
    
    loaded = load_context()
    assert loaded.active_project_id == "uuid-1234"
    assert loaded.active_project_name == "Test Project"
    assert loaded.user_preferences["editor"] == "vim"


def test_load_corrupt_context(temp_context_dir, monkeypatch):
    """Should return defaults if the file is corrupt JSON."""
    monkeypatch.setattr("cli.context.settings.cli_config_dir", temp_context_dir)
    (temp_context_dir / "context.json").write_text("{invalid-json", encoding="utf-8")
    
    ctx = load_context()
    assert ctx.active_project_id is None


def test_require_context_decorator_success(temp_context_dir, monkeypatch):
    """Decorator should allow execution if project is active."""
    monkeypatch.setattr("cli.context.settings.cli_config_dir", temp_context_dir)
    # Setup active context
    ctx = CliContext(active_project_id="project-1")
    save_context(ctx)
    
    app = typer.Typer()
    
    # Using a command group approach to ensure registration works as expected in tests
    @app.command()
    @require_context
    def dummy():
        typer.echo("Success!")
        
    # The trick with Typer testing is that if there's only one command, it's the "main" command.
    # So we call invoke(app, []) for "main". 
    # But if we want to simulate "typer app <command>", we should probably not use the simplified single-command mode.
    # However, for this unit test, we just want to verify the decorator runs.
    
    # Try invoking with NO args (main command mode)
    result = runner.invoke(app, [])
    
    if result.exit_code != 0:
         print(f"Stdout: {result.stdout}")
         print(f"Exception: {result.exception}")

    assert result.exit_code == 0
    assert "Success!" in result.stdout


def test_require_context_decorator_failure(temp_context_dir, monkeypatch):
    """Decorator should abort execution if no project is active."""
    monkeypatch.setattr("cli.context.settings.cli_config_dir", temp_context_dir)
    # Ensure clean state (no active project)
    (temp_context_dir / "context.json").unlink(missing_ok=True)
    
    app = typer.Typer()
    
    @app.command()
    def dummy():
        typer.echo("Should not run")

    app.command()(require_context(dummy))
        
    result = runner.invoke(app, ["dummy"])
    assert result.exit_code == 1
    assert "❌ No active project selected" in result.stdout
    assert "Should not run" not in result.stdout
