# Backend & Data Layer Documentation

This document details the backend architecture, data models, and storage mechanisms for **Re:Search**. The system is built on **Tauri 2.0 (Rust)** with a local-first **SQLite** database enhanced by vector search capabilities.

## 1. Core Architecture

The backend runs as a subprocess within the Tauri application shell. It is responsible for all heavy lifting, including file I/O, database management, web scraping, and AI inference orchestration.

### Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Runtime** | **Rust** (Tauri 2.0) | Core logic, OS interaction, high performance. |
| **Database** | **SQLite** | Primary relational store (metadata, structure). |
| **Vector Engine** | **sqlite-vec** | Extension for storing and searching semantic embeddings. |
| **Search Engine** | **FTS5** | SQLite extension for full-text search. |
| **File System** | **std::fs** + **tokio** | Managing raw markdown artifacts and assets. |
| **HTTP Client** | **reqwest** | Fetching web content for the scraper. |

---

## 2. The "Universal Node" Data Model

The entire application state is represented as a graph of **Nodes** connected by **Edges**. This allows for a flexible, "Roam Research"-style knowledge graph.

### 2.1. The Node Concept

Every entity in the system—whether it's a markdown document, a web source, an image, or a chat log—is a **Node**.

#### Rust Struct Representation
```rust
use serde::{Serialize, Deserialize};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub enum NodeType {
    Artifact, // A user-created markdown note
    Source,   // An external web page or PDF
    Concept,  // An abstract idea or tag
    Chat,     // A conversation history
    Image,    // A visual asset
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Node {
    pub id: String,          // UUID v4
    pub node_type: NodeType, // Enum as string in DB
    pub title: String,       // Display name
    pub content_path: Option<String>, // Relative path to file (if content is large)
    pub metadata: String,    // JSON blob (tags, source_url, author, etc.)
    pub created_at: i64,     // Unix timestamp
    pub updated_at: i64,     // Unix timestamp
}
```

### 2.2. The Edge Concept

Relationships between nodes are directional.

#### Rust Struct Representation
```rust
#[derive(Debug, Serialize, Deserialize)]
pub struct Edge {
    pub source_id: String,
    pub target_id: String,
    pub relation_type: String, // e.g., "mentions", "child_of", "related_to"
}
```

---

## 3. Database Schema (SQLite)

The database acts as the index and metadata store. Actual heavy content (long text) is often offloaded to the filesystem, but indexed here for search.

### 3.1. Main Tables

```sql
-- Enable Foreign Keys
PRAGMA foreign_keys = ON;

-- Nodes Table
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content_path TEXT, -- Nullable. If NULL, content might be in 'content_text' or just metadata.
    metadata TEXT DEFAULT '{}', -- JSON
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- Edges Table
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT DEFAULT 'related',
    created_at INTEGER DEFAULT (unixepoch()),
    PRIMARY KEY (source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- Index for graph traversals
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
```

### 3.2. Search Tables (FTS5 & Vector)

To enable "Hybrid Search" (Keyword + Semantic), we use two specialized virtual tables.

**Full-Text Search (FTS5):**
```sql
-- Virtual table for fast keyword search
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    id UNINDEXED,
    title,
    content_body, -- Extracted text content for searching
    tokenize = 'porter'
);

-- Trigger to keep FTS updated
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(id, title, content_body) VALUES (new.id, new.title, ''); -- Content updated via app logic
END;
```

**Vector Search (sqlite-vec):**
*Note: `sqlite-vec` stores embeddings as BLOBs.*

```sql
-- Virtual table for vector similarity search
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding FLOAT[1536] -- Dimension depends on model (e.g., 1536 for OpenAI, 384 for mini-lm)
);
```

---

## 4. File System Operations

While the database holds structure, the **File System** holds the truth. This "File-First" approach ensures user data is portable and not locked into a `.db` file.

### 4.1. Directory Structure

The application workspace (`~/.research_data/`) is structured as follows:

```
/workspace
  /artifacts       # User-created .md files
  /sources         # Scraped content (HTML/PDF)
  /assets          # Images/Attachments
  library.db       # SQLite Database
```

### 4.2. Markdown Serialization

When a user edits a node of type `Artifact`, the backend performs the following:

1.  **Read:** `fs::read_to_string(path)` -> Send string to Frontend.
2.  **Write:** Frontend sends content -> `fs::write(path, content)`.
3.  **Sync:** Update `nodes` table `updated_at` and trigger a re-indexing for FTS/Vector.

**Frontmatter Handling:**
We use YAML frontmatter to store metadata inside the markdown files, ensuring they are useful even outside the app (e.g., in Obsidian).

```markdown
---
id: 550e8400-e29b-41d4-a716-446655440000
type: artifact
tags: [history, paris]
created: 2023-10-27
---

# The actual content...
```

---

## 5. Tauri Command Interface

The frontend (React) communicates with Rust via **Tauri Commands**. These are async functions exposed to the webview.

### 5.1. Command Definitions

**Node Operations:**
```rust
#[tauri::command]
fn create_node(title: String, node_type: String) -> Result<Node, String>;

#[tauri::command]
fn get_node(id: String) -> Result<Node, String>;

#[tauri::command]
fn save_node_content(id: String, content: String) -> Result<(), String>;

#[tauri::command]
fn delete_node(id: String) -> Result<(), String>;
```

**Graph Operations:**
```rust
#[tauri::command]
fn connect_nodes(source: String, target: String, label: String) -> Result<(), String>;

#[tauri::command]
fn get_graph_data() -> Result<GraphPayload, String>; // Returns nodes + edges for React Flow
```

**Search Operations:**
```rust
#[tauri::command]
fn search_nodes(query: String, mode: String) -> Result<Vec<Node>, String>; 
// mode: "fuzzy" (FTS) | "semantic" (Vector) | "hybrid"
```

**AI Agent Operations:**
```rust
#[tauri::command]
async fn run_research_agent(goal: String) -> Result<String, String>;
// Triggers the LangGraph/Python sidecar or Rust-native agent loop
```

---

## 6. Implementation Notes for Developers

1.  **Database Migration:** Use `sqlx` or `rusqlite` with built-in migration scripts to ensure the schema is created on first run.
2.  **Vector Loading:** `sqlite-vec` must be loaded as a dynamic extension at runtime. Ensure the `.dll`/`.so`/`.dylib` is bundled with the Tauri app.
3.  **Concurrency:** SQLite writes are blocking. Use a dedicated thread or connection pool (like `r2d2`) for DB operations to avoid freezing the UI.
4.  **Error Handling:** All Tauri commands return `Result<T, String>` to gracefully handle FS/DB errors in the frontend.
