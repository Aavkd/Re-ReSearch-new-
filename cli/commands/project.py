"""Project management commands."""

import json
import typer
from pathlib import Path

from backend.db import get_connection, init_db
from backend.db.projects import (
    create_project,
    list_projects,
    get_project_summary,
    export_project,
    get_project_nodes,
)
from cli.context import load_context, save_context, require_context

project_app = typer.Typer(help="Manage research projects (workspaces).")


@project_app.command("new")
def project_new(
    name: str = typer.Argument(..., help="Name of the new project.")
) -> None:
    """Create a new project and switch to it."""
    conn = get_connection()
    init_db(conn)
    
    try:
        node = create_project(conn, name)
        typer.echo(f"✅ Project created: {node.title} ({node.id})")
        
        # Auto-switch context
        ctx = load_context()
        ctx.active_project_id = node.id
        ctx.active_project_name = node.title
        save_context(ctx)
        
        typer.echo(f"📂 Switched to project: {node.title}")
    finally:
        conn.close()


@project_app.command("list")
def project_list() -> None:
    """List all available projects."""
    conn = get_connection()
    init_db(conn)
    
    try:
        projects = list_projects(conn)
        if not projects:
            typer.echo("No projects found.")
            return

        ctx = load_context()
        active_id = ctx.active_project_id

        typer.echo("Projects:")
        for p in projects:
            marker = "*" if p.id == active_id else " "
            typer.echo(f"{marker} {p.title} \t[{p.id}]")
    finally:
        conn.close()


@project_app.command("switch")
def project_switch(
    identifier: str = typer.Argument(..., help="Project Name or UUID.")
) -> None:
    """Switch the active project context."""
    conn = get_connection()
    init_db(conn)
    
    try:
        # Try finding by ID first
        projects = list_projects(conn)
        target = None
        
        for p in projects:
            if p.id == identifier:
                target = p
                break
            if p.title == identifier:
                target = p
                break
        
        if not target:
            # Fallback: fuzzy match? For now strict.
            typer.echo(f"❌ Project '{identifier}' not found.")
            raise typer.Exit(code=1)
            
        ctx = load_context()
        ctx.active_project_id = target.id
        ctx.active_project_name = target.title
        save_context(ctx)
        
        typer.echo(f"📂 Switched to project: {target.title}")
    finally:
        conn.close()


@project_app.command("status")
@require_context
def project_status() -> None:
    """Show dashboard for the current project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        summary = get_project_summary(conn, ctx.active_project_id)
        
        typer.echo(f"\n📊 Project: {ctx.active_project_name}")
        typer.echo(f"   ID: {ctx.active_project_id}")
        typer.echo("-" * 40)
        typer.echo(f"   Total Nodes: {summary['total_nodes']}")
        
        typer.echo("\n   By Type:")
        for type_, count in summary["by_type"].items():
            typer.echo(f"    - {type_}: {count}")
            
        if summary["recent_artifacts"]:
            typer.echo("\n   Recent Artifacts:")
            for title in summary["recent_artifacts"]:
                typer.echo(f"    - {title}")
        
        typer.echo("")
    finally:
        conn.close()


@project_app.command("export")
@require_context
def project_export(
    output: Path = typer.Option(None, help="Output JSON file path. Defaults to <project_name>.json")
) -> None:
    """Export the project graph to a JSON file."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        data = export_project(conn, ctx.active_project_id)
        
        if not output:
            # Sanitize filename
            safe_name = "".join(c for c in ctx.active_project_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            output = Path(f"{safe_name}.json")
            
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        typer.echo(f"✅ Exported to {output.absolute()}")
    finally:
        conn.close()
