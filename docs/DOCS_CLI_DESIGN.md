# Design Specification: Re:Search CLI (The Headless Library)

## 1. Overview & Philosophy

The **Re:Search CLI** is not merely a debugging tool for the backend; it is the **Text-Based User Interface (TUI)** for the *Library of Alexandria*.

It is designed to be a **functional prototype of the future Frontend**, validating the core user journeys (Project Management, Research, Synthesis, Connection) before a single pixel of UI is drawn.

### Core Principles
1.  **Stateful & Persistent:** The CLI remembers where you are ("Active Project") and preserves context between commands.
2.  **Graph-First:** Every action (search, write, scrape) manipulates the underlying Node/Edge graph.
3.  **Editor-Agnostic:** The CLI integrates with the user's preferred text editor (Vim, Nano, VS Code) to handle the "Deep Work" phase, syncing changes back to the DB.
4.  **Agent-Centric:** AI agents are treated as "Staff" you hire for specific tasks within a project context.

---

## 2. Architecture: The "Headless" Stack

The CLI sits on top of the existing Backend layers, orchestrating them into coherent workflows.

```mermaid
graph TD
    User((User)) --> CLI[Re:Search CLI]
    CLI -- "Context (Project ID)" --> StateFile[~/.research_context]
    CLI -- "CRUD + Graph Ops" --> Backend[Python Backend]
    Backend -- "SQL/Vector" --> DB[(SQLite + Vec)]
    Backend -- "Crawl/Parse" --> Web[The Internet]
    Backend -- "Inference" --> LLM[Local/Cloud Models]
    
    subgraph "The Workspace"
        Drafts[Temp Markdown Files]
        Editor[External Editor (Code/Vim)]
    end
    
    CLI -- "Sync" --> Drafts
    Drafts <--> Editor
```

---

## 3. User Journey & Command Structure

The CLI is organized around the **Mental Model** of the concept:
- **Project** = The Workspace
- **Map** = The Canvas / Crazy Board
- **Library** = The Deep Memory / Sources
- **Draft** = The Artifact / Editor
- **Agent** = The Researcher

### 3.1. `project` — The Workspace Manager

**Goal:** Manage isolated contexts for different research topics.

- `project new <name>`
  - Creates a "Project" node in the DB.
  - Sets it as the **Active Project**.
- `project switch <name|id>`
  - Updates the local state file to point to this project.
  - All subsequent commands (search, add, agent) are scoped to this project.
- `project status`
  - Displays a dashboard: "Project: Paris 19ème | 15 Sources | 4 Artifacts | 2 Agents Running".
- `project export`
  - Dumps the entire project graph to JSON/Markdown for backup.

### 3.2. `library` — The Curator (Input)

**Goal:** Feed the "Deep Memory". Replaces `scrape` and `ingest`.

- `library add <url|file>`
  - **Context-Aware:** Ingests the source *and* automatically creates an edge: `(Project) -> [HAS_SOURCE] -> (SourceNode)`.
  - Tags the source with the project ID.
- `library search "<query>"`
  - **Scoped Search:** Performs Hybrid Search *only* on nodes connected to the Active Project (or global if flag `--global` is set).
- `library recall "<question>"`
  - **Omniscient Chat:** Uses the Project's context to answer questions directly (RAG).
  - *User:* "Who was the prefect of police?" -> *Agent:* "Based on 'Source A' and 'Source B', it was..."

### 3.3. `map` — The Graph Manager (Structure)

**Goal:** Simulate the "Crazy Board" connections.

- `map show`
  - Renders an ASCII tree or list of the current project's immediate graph.
- `map connect <NodeA> <NodeB> --label "<relation>"`
  - Creates a semantic edge between two nodes.
  - *Example:* `map connect "Vidocq" "Sureté" --label "FOUNDED"`
- `map cluster`
  - (Advanced) Uses an LLM to auto-detect themes and propose clusters/connections within the project.

### 3.4. `draft` — The Creator (Output)

**Goal:** The "VS Code" experience. Writing artifacts based on research.

- `draft new "<Title>"`
  - Creates an empty "Artifact" node linked to the Project.
- `draft edit <NodeID>`
  - **The Magic Loop:**
    1.  Fetches `content` from DB.
    2.  Writes to a temp file: `/tmp/research_session/Vidocq_Bio.md`.
    3.  Spawns `$EDITOR` (e.g., `code -w` or `vim`).
    4.  Waits for process exit.
    5.  Reads file, updates DB `content`, updates `updated_at`.
- `draft attach <NodeID> <SourceID>`
  - Explicitly links a source to a draft (Citation).

### 3.5. `agent` — The Staff (Automation)

**Goal:** Delegation.

- `agent hire --goal "<objective>"`
  - Spawns a background `Researcher Agent`.
  - **Auto-Link:** The Agent's final report is saved as an Artifact linked to the Project.
  - **Auto-Source:** All found URLs are added to the Library and linked to the Project.
- `agent status`
  - Shows active background jobs.

---

## 4. Technical Specifications

### 4.1. Persistence (State Management)
The CLI needs to know "Where am I?".

- **Location:** `~/.research_cli/context.json`
- **Schema:**
  ```json
  {
    "active_project_id": "uuid-...",
    "active_project_name": "Paris 19ème",
    "user_preferences": {
        "editor_command": "code -w",
        "default_search_depth": "deep"
    }
  }
  ```
- **Loader:** A Python decorator `@require_context` will load this state before executing project-scoped commands.

### 4.2. Database Schema Updates (Requirements)
To support this CLI, the DB schema needs minor extensions (if not already present):

1.  **`project_id` column** (or `projects` table + join table) on Nodes to allow scoping.
    *   *Alternative:* Use the existing Graph! A "Project" is just a Node of type `Project`. "Scope" is defined by traversing `(Project) -> * -> (Node)`.
    *   *Decision:* **Graph-based scoping.** The "Active Project" is just a Root Node ID. Queries filter by "is connected to Root Node (depth 1 or 2)".

### 4.3. The "Edit Loop" Implementation
Python's `subprocess` and `tempfile` modules will handle the editor integration.

```python
import tempfile, subprocess, os

def edit_node_content(content: str, extension=".md") -> str:
    editor = os.getenv("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False, mode='w+') as tf:
        tf.write(content)
        tf_path = tf.name
    
    try:
        subprocess.call([editor, tf_path])
        with open(tf_path, 'r') as f:
            new_content = f.read()
    finally:
        os.remove(tf_path)
    
    return new_content
```

---

## 5. Future-Proofing for Frontend

This CLI design explicitly prepares the data structures for the Tauri Frontend:

1.  **Projects:** Directly maps to the "Project Picker" UI.
2.  **Map:** Populates the `edges` table, which the Canvas will render visually.
3.  **Drafts:** The `content` field in DB is the source of truth; the UI will just be another "Editor" like Vim.

By building this CLI, we ensure the Backend API is robust enough to support the full GUI application.
