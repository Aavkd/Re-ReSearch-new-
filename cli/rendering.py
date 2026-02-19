"""Utilities for rendering graphs in the CLI."""

from __future__ import annotations

from typing import Dict, List, Set, Any
from backend.db.models import Node, Edge

def render_tree(nodes: List[Node], edges: List[Dict[str, Any]], root_id: str) -> str:
    """Render a project graph as an ASCII tree.
    
    Args:
        nodes: List of Node objects.
        edges: List of dicts (source, target, relation).
        root_id: The ID of the root node (Project).
        
    Returns:
        String representation of the tree.
    """
    # Build adjacency list
    adj = {}
    node_map = {n.id: n for n in nodes}
    
    # Also add root if not in nodes list?
    # Assume root_id is the Project node, and nodes list contains content.
    # We need to find edges from root to content.
    
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        rel = e["relation"]
        
        if src not in adj:
            adj[src] = []
        adj[src].append((tgt, rel))
        
    # Recursive render
    lines = []
    visited = set()
    
    def _visit(node_id: str, prefix: str = "", is_last: bool = True):
        if node_id in visited:
            lines.append(f"{prefix}└── [Recursive Cycle] {node_id[:8]}")
            return
        visited.add(node_id)
        
        node = node_map.get(node_id)
        title = node.title if node else f"Unknown({node_id[:8]})"
        type_icon = _get_icon(node.node_type if node else "")
        
        # Determine connector
        connector = "└── " if is_last else "├── "
        
        # For root, we don't show connector
        if prefix == "":
            lines.append(f"{type_icon} {title}")
            child_prefix = ""
        else:
            lines.append(f"{prefix}{connector}{type_icon} {title}")
            child_prefix = prefix + ("    " if is_last else "│   ")
            
        # Get children
        children = adj.get(node_id, [])
        # Sort by relation?
        children.sort(key=lambda x: x[1])
        
        count = len(children)
        for i, (child_id, rel) in enumerate(children):
            # Annotate relation?
            # We can put relation in the line above or inline.
            # Let's try inline: [REL] Node
            
            # _visit(child_id, child_prefix, i == count - 1)
            # Wait, we want to show relation.
            
            child_node = node_map.get(child_id)
            child_title = child_node.title if child_node else f"Unknown({child_id[:8]})"
            child_icon = _get_icon(child_node.node_type if child_node else "")
            
            child_connector = "└── " if (i == count - 1) else "├── "
            
            lines.append(f"{child_prefix}{child_connector}[{rel}] {child_icon} {child_title}")
            
            # Recurse? 
            # If we just print children here, we don't recurse deeper.
            # If we want deep tree, we need to recurse.
            # But the 'lines.append' above is printing the child.
            # So _visit should be called FOR the child.
            
            # Refactor: _visit prints THE node.
            # But we need relation from parent.
            pass

    # New strategy:
    # _visit(node_id, relation_from_parent, prefix, is_last)
    
    visited = set()
    
    def _render_node(node_id: str, relation: str, prefix: str, is_last: bool, is_root: bool):
        if node_id in visited and not is_root:
            # Cycle or multi-parent
            # lines.append(f"{prefix}└── [Ref] {node_id[:8]}...")
            return
            
        visited.add(node_id)
        node = node_map.get(node_id)
        
        if not node and not is_root:
             return
             
        title = node.title if node else f"Unknown({node_id[:8]})"
        type_icon = _get_icon(node.node_type if node else "")
        
        if is_root:
            lines.append(f"{type_icon} {title}")
            child_prefix = ""
        else:
            connector = "└── " if is_last else "├── "
            # Include relation label
            lines.append(f"{prefix}{connector}[{relation}] {type_icon} {title}")
            child_prefix = prefix + ("    " if is_last else "│   ")
            
        children = adj.get(node_id, [])
        count = len(children)
        for i, (child_id, rel) in enumerate(children):
            _render_node(child_id, rel, child_prefix, i == count - 1, False)

    # Start
    # We need the root object to start
    root_node = node_map.get(root_id)
    if root_node:
        _render_node(root_id, "", "", True, True)
    else:
        # Fallback: just list disjoint trees?
        lines.append("Root node not found in subgraph.")
        
    return "\n".join(lines)


def _get_icon(node_type: str) -> str:
    icons = {
        "Project": "📁",
        "Source": "📄",
        "Artifact": "📝",
        "Concept": "💡",
        "Image": "🖼️",
    }
    return icons.get(node_type, "📦")
