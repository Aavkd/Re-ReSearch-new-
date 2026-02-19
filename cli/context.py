"""Persistent state management for the Re:Search CLI.

Tracks the "active project" and user preferences.
Stored in `~/.research_cli/context.json`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import typer
from backend.config import settings


@dataclass
class CliContext:
    active_project_id: str | None = None
    active_project_name: str | None = None
    user_preferences: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> CliContext:
        try:
            raw = json.loads(data)
            return cls(**raw)
        except (json.JSONDecodeError, TypeError):
            return cls()


def _get_context_path() -> Path:
    """Return the path to the context JSON file."""
    return settings.cli_config_dir / "context.json"


def load_context() -> CliContext:
    """Load the CLI context from disk. Returns defaults if missing/corrupt."""
    path = _get_context_path()
    if not path.exists():
        return CliContext()
    
    try:
        return CliContext.from_json(path.read_text(encoding="utf-8"))
    except Exception:
        return CliContext()


def save_context(ctx: CliContext) -> None:
    """Save the CLI context to disk."""
    settings.cli_config_dir.mkdir(parents=True, exist_ok=True)
    _get_context_path().write_text(ctx.to_json(), encoding="utf-8")


def require_context(func: Callable) -> Callable:
    """Decorator for CLI commands that require an active project.
    
    Injects `ctx` (CliContext) as the first argument to the wrapped function.
    Aborts execution if no project is active.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ctx = load_context()
        if not ctx.active_project_id:
            typer.echo("❌ No active project selected.")
            typer.echo("Run 'project new <name>' or 'project switch <name>' first.")
            raise typer.Exit(code=1)
        
        # Pass context to the function
        # Note: Typer commands don't support arbitrary args well if not typed.
        # But we can assume the caller will handle it or we use ctx global.
        # Better pattern for Typer: rely on the side-effect or pass explicitly if needed.
        # Here we just validate, and the command can call load_context() if it needs data.
        return func(*args, **kwargs)
    
    return wrapper
