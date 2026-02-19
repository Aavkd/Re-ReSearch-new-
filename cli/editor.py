"""External editor integration for the Re:Search CLI.

Handles opening nodes in the user's preferred editor ($EDITOR) and syncing
changes back to the database.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.db.nodes import get_node, update_node
from cli.context import load_context


def get_editor_command() -> str:
    """Determine the editor command to use."""
    ctx = load_context()
    
    # 1. User preference from context.json
    if "editor" in ctx.user_preferences:
        return ctx.user_preferences["editor"]
        
    # 2. Environment variable
    if "EDITOR" in os.environ:
        return os.environ["EDITOR"]
        
    # 3. Platform defaults
    if os.name == "nt":  # Windows
        # Check for VS Code first
        if shutil.which("code"):
            return "code -w"
        return "notepad"
    else:  # Unix
        if shutil.which("vim"):
            return "vim"
        if shutil.which("nano"):
            return "nano"
        return "vi"


def edit_node_content(
    conn, 
    node_id: str, 
    extension: str = ".md"
) -> Optional[str]:
    """Open a node's content in an external editor and save changes.

    Returns the new content if changed, or None if cancelled/unchanged.
    """
    node = get_node(conn, node_id)
    if not node:
        raise ValueError(f"Node {node_id} not found.")

    # Determine initial content
    content = ""
    if node.content_path:
        # Load from file if path exists
        # content_path is relative to workspace root usually? 
        # Or absolute? Let's assume relative to workspace_dir for now.
        # But wait, implementation plan said we store content in a file.
        # Let's assume content_path is relative to settings.workspace_dir
        
        full_path = settings.workspace_dir / node.content_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
    
    # Create temp file in persistent draft location
    drafts_dir = settings.cli_config_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize title for filename
    safe_title = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title.replace(' ', '_') or "untitled"
    
    draft_file = drafts_dir / f"{safe_title}_{node.id[:8]}{extension}"
    draft_file.write_text(content, encoding="utf-8")
    
    # Launch editor
    editor = get_editor_command()
    cmd = f"{editor} \"{draft_file}\""
    
    # Shell=True to handle spaces in command (e.g. "code -w")
    ret = subprocess.call(cmd, shell=True)
    
    if ret != 0:
        print(f"⚠️ Editor exited with code {ret}")
        return None
        
    # Read back
    new_content = draft_file.read_text(encoding="utf-8")
    
    if new_content == content:
        return None  # No change
        
    # Save back to DB
    # We need to decide: store in content_path file or metadata?
    # Plan said: "Use content_path. The draft edit flow writes to ~/.research_cli/drafts/<node_id>.md and sets content_path accordingly."
    
    # WAIT: If we set content_path to the draft file, we are linking the DB to ~/.research_cli/drafts.
    # That works! It keeps the content out of the DB file.
    # But content_path should be relative if we want portability.
    # If we point to absolute path in .research_cli, it breaks if we move the workspace.
    
    # Better approach: Copy the draft to the workspace's "content" folder and link that.
    content_dir = settings.workspace_dir / "content"
    content_dir.mkdir(exist_ok=True)
    
    final_path = content_dir / f"{node.id}.md"
    final_path.write_text(new_content, encoding="utf-8")
    
    # Update node with relative path
    rel_path = f"content/{node.id}.md"
    update_node(conn, node.id, content_path=rel_path)
    
    return new_content
