"""Draft commands for creating and editing artifacts."""

import subprocess
import tempfile
import typer
from pathlib import Path
import os
import shutil

from backend.db import get_connection, init_db
from backend.db.nodes import create_node, get_node, update_node, list_nodes
from backend.db.projects import link_to_project, get_project_nodes
from backend.config import settings

from cli.context import load_context, require_context
from cli.editor import get_editor_command

draft_app = typer.Typer(help="Create and edit artifacts (drafts).")


def _open_editor(file_path: Path) -> None:
    """Open the user's preferred editor on the given file path."""
    editor = os.environ.get("EDITOR")
    if not editor:
        # Fallback detection
        if shutil.which("code"):
            editor = "code -w"  # Wait for file to close
        elif shutil.which("vim"):
            editor = "vim"
        elif shutil.which("nano"):
            editor = "nano"
        elif os.name == "nt":
            editor = "notepad"
        else:
            editor = "vi"

    # Split command for subprocess if needed, but shell=True is simpler for "code -w"
    try:
        subprocess.check_call(f'{editor} "{file_path}"', shell=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"⚠️ Editor exited with error code {e.returncode}")


@draft_app.command("new")
@require_context
def draft_new(
    title: str = typer.Argument(..., help="Title of the new artifact."),
) -> None:
    """Create a new artifact and link it to the active project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)

    try:
        # Create Artifact Node
        node = create_node(conn, title=title, node_type="Artifact")
        
        # Link to Project
        link_to_project(conn, ctx.active_project_id, node.id, relation="HAS_ARTIFACT")
        
        # Initialize empty content file
        content_dir = settings.workspace_dir / "content"
        content_dir.mkdir(exist_ok=True)
        content_path = content_dir / f"{node.id}.md"
        content_path.write_text(f"# {title}\n\n", encoding="utf-8")
        
        # Update node with content path (relative to workspace)
        rel_path = f"content/{node.id}.md"
        update_node(conn, node.id, content_path=rel_path)

        typer.echo(f"✅ Draft created: {title} ({node.id})")
        typer.echo(f"📝 Content file: {content_path}")
        
        # Optional: Ask to open immediately?
        if typer.confirm("Open in editor now?", default=True):
             _open_editor(content_path)
             typer.echo("✅ Saved.")

    finally:
        conn.close()


@draft_app.command("edit")
@require_context
def draft_edit(
    node_id: str = typer.Argument(..., help="ID of the artifact to edit.")
) -> None:
    """Open an existing artifact in the configured editor."""
    conn = get_connection()
    init_db(conn)

    try:
        node = get_node(conn, node_id)
        if not node:
            typer.echo(f"❌ Node {node_id} not found.")
            raise typer.Exit(code=1)
            
        if not node.content_path:
            typer.echo(f"⚠️ Node has no content path. Creating one...")
            content_dir = settings.workspace_dir / "content"
            content_dir.mkdir(exist_ok=True)
            content_path = content_dir / f"{node.id}.md"
            content_path.touch()
            update_node(conn, node.id, content_path=f"content/{node.id}.md")
        else:
            content_path = settings.workspace_dir / node.content_path
            
        if not content_path.exists():
            # If path exists in DB but file missing, recreate
             content_path.parent.mkdir(parents=True, exist_ok=True)
             content_path.touch()

        typer.echo(f"📝 Opening {node.title}...")
        _open_editor(content_path)
        typer.echo("✅ Saved.")
        
        # Update timestamp
        update_node(conn, node.id) # trigger updated_at
        
    finally:
        conn.close()


@draft_app.command("list")
@require_context
def draft_list() -> None:
    """List artifacts in the current project."""
    ctx = load_context()
    conn = get_connection()
    init_db(conn)
    
    try:
        # Get all nodes in project, filter by type Artifact
        # Or better, list all artifacts and check linkage?
        # Use get_project_nodes with type filtering logic in Python
        nodes = get_project_nodes(conn, ctx.active_project_id, depth=2)
        artifacts = [n for n in nodes if n.node_type == "Artifact"]
        
        if not artifacts:
            typer.echo("No drafts found in this project.")
            return
            
        typer.echo(f"Drafts in {ctx.active_project_name}:")
        for art in artifacts:
            typer.echo(f" - {art.title} [{art.id}]")
            
    finally:
        conn.close()


@draft_app.command("show")
@require_context
def draft_show(
    node_id: str = typer.Argument(..., help="ID of the artifact.")
) -> None:
    """Print the content of an artifact to stdout."""
    conn = get_connection()
    init_db(conn)
    
    try:
        node = get_node(conn, node_id)
        if not node:
            typer.echo(f"❌ Node {node_id} not found.")
            return
            
        if node.content_path:
            path = settings.workspace_dir / node.content_path
            if path.exists():
                typer.echo("-" * 40)
                typer.echo(path.read_text(encoding="utf-8"))
                typer.echo("-" * 40)
            else:
                typer.echo("(File missing on disk)")
        else:
            typer.echo("(No content path)")
    finally:
        conn.close()
