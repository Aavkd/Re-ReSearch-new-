# Re:Search — Current State Report
> Last audited: February 2026. Written against actual code, not documentation.

---

## 1. What This Project Is

**Re:Search** is a local-first AI research assistant. You give it a goal; it searches the web, scrapes pages, chunks and embeds the content into a local SQLite vector database, then uses an LLM to synthesise a markdown report.

The stack is **Python-only**:
- **Backend** — FastAPI HTTP API, SQLite + sqlite-vec, LangGraph agent, RAG pipeline
- **CLI** — Typer command-line interface (partially wired)
- **No frontend** — The `docs/DOCS_FRONTEND.md` and `docs/DOCS_AI_CORE.md` describe an abandoned Rust/Tauri design that was never built

Data lives in `~/.research_data/library.db` by default. CLI state lives in `~/.research_cli/context.json`.

---

## 2. Architecture Overview

```
CLI (Typer)
└── calls backend modules directly (no HTTP)

FastAPI API  (uvicorn)
├── /nodes    — CRUD for graph nodes
├── /search   — FTS / vector / hybrid search
├── /ingest   — URL and PDF ingestion
└── /research — SSE streaming agent run

Backend
├── db/       — SQLite primitives (nodes, edges, search, projects)
├── scraper/  — httpx + trafilatura scraper (Playwright fallback for SPAs)
├── rag/      — chunker, embedder (Ollama/OpenAI), ingestor, PDF ingestor
└── agent/    — LangGraph researcher (planner→searcher→scraper→synthesiser→evaluator)
```

---

## 3. Configuration

All settings live in `backend/config.py` as a `Settings` dataclass, backed by environment variables. A `.env` file at the workspace root is auto-loaded.

| Variable | Default | Purpose |
|---|---|---|
| `RESEARCH_WORKSPACE` | `~/.research_data` | DB and content storage root |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma:latest` | Embedding model name |
| `OLLAMA_CHAT_MODEL` | `ministral-3:8b` | Chat/LLM model name |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OPENAI_API_KEY` | *(unset)* | Required if using OpenAI |
| `BRAVE_API_KEY` | `""` | Optional; enables Brave Search |
| `SEARXNG_BASE_URL` | `https://searx.be` | SearXNG search instance |
| `EMBEDDING_DIM` | `768` | Vector dimension (must match model) |
| `AGENT_MAX_ITERATIONS` | `5` | Research loop cap |
| `SCRAPE_CONCURRENCY` | `5` | Parallel scrape threads |

**Minimum to run (Ollama path):** Ollama running locally with `embeddinggemma:latest` pulled for embeddings and `ministral-3:8b` pulled for the LLM.

---

## 4. Database

**File:** `~/.research_data/library.db`

**Schema (auto-initialised on first run):**

| Table | Purpose |
|---|---|
| `nodes` | Every entity (Source, Chunk, Artifact, Project, Concept…) |
| `edges` | Directed relations between nodes (`HAS_SOURCE`, `HAS_ARTIFACT`, `has_chunk`, `CITES`, …) |
| `nodes_fts` | FTS5 virtual table for keyword search (BM25, porter stemmer) |
| `nodes_vec` | sqlite-vec virtual table for vector/KNN search |

All schema operations are idempotent (`IF NOT EXISTS`). No migration scripts have been written yet (the `MIGRATIONS` list in `backend/db/migrations.py` is empty by design).

---

## 5. Component Status

### ✅ Fully Complete

| Component | File(s) | Notes |
|---|---|---|
| DB primitives | `backend/db/nodes.py`, `edges.py`, `search.py` | Full CRUD, FTS, vector, hybrid search with scope filtering |
| Graph scoping | `backend/db/projects.py` | Recursive CTE BFS; create/list/link/summary/export |
| Scraper | `backend/scraper/fetcher.py`, `extractor.py` | httpx + Playwright SPA fallback; trafilatura + BS4 extraction |
| RAG ingestor | `backend/rag/ingestor.py`, `pdf_ingestor.py` | URL and PDF ingestion pipelines — chunk, embed, store |
| Embedder | `backend/rag/embedder.py` | Ollama and OpenAI providers |
| Chunker | `backend/rag/chunker.py` | Recursive split with overlap |
| Agent | `backend/agent/` | LangGraph researcher; full plan→search→scrape→synthesise→evaluate loop |
| Search providers | `backend/agent/search_providers.py` | Brave → SearXNG → DuckDuckGo chain with fallbacks |
| FastAPI API | `backend/api/` | All 4 routers fully implemented |
| CLI context | `cli/context.py` | `context.json` read/write, `require_context` decorator |
| CLI editor | `cli/editor.py` | External editor integration with draft file write-back |
| CLI rendering | `cli/rendering.py` | ASCII tree renderer (minor dead code, non-blocking) |
| `project` commands | `cli/commands/project.py` | new, list, switch, status, export — all implemented |
| `library` commands | `cli/commands/library.py` | add (URL/PDF), list, search (scoped/global) — all implemented |
| `map` commands | `cli/commands/map.py` | show (tree), connect — implemented |
| `draft` commands | `cli/commands/draft.py` | new, edit, list, show — implemented (see bug below) |
| Tests | `tests/` | ~10 test files covering all backend layers and most CLI commands |

---

## 6. Known Bugs

### 🐛 BUG — `draft edit` crashes on timestamp update
**File:** `cli/commands/draft.py`, `draft_edit()` command  
**Problem:** After the editor closes, the command calls `update_node(conn, node.id)` with no keyword arguments. The `update_node` function raises `ValueError: No valid fields provided` because `updates` is empty.  
**Fix:** Change the call to `update_node(conn, node.id, updated_at=int(time.time()))` (or any valid field).

---

## 7. What's Incomplete

### 🔌 CRITICAL — `cli/main.py` does NOT mount the new command groups
All 4 new command groups (`project`, `library`, `map`, `draft`) **exist as Python modules** in `cli/commands/` but are **never registered** with the main Typer app in `cli/main.py`.

Running `python cli/main.py --help` still shows the old flat commands (`db`, `scrape`, `ingest`, `research`). The new commands are **unreachable** from the CLI entry-point.

**Fix required in `cli/main.py`:**
```python
from cli.commands.project import project_app
from cli.commands.library import library_app
from cli.commands.map import map_app
from cli.commands.draft import draft_app

app.add_typer(project_app, name="project")
app.add_typer(library_app, name="library")
app.add_typer(map_app, name="map")
app.add_typer(draft_app, name="draft")
```

### 📋 Missing commands (not yet implemented, planned in Phase 9–12)

| Command | Status | Notes |
|---|---|---|
| `library recall "<question>"` | ❌ Not built | RAG-based Q&A for active project; needs `backend/rag/recall.py` |
| `map cluster` | ❌ Not built | LLM auto-clustering of project nodes |
| `draft attach <node_id> <source_id>` | ❌ Not built | Create `CITES` edge between artifact and source |
| `agent hire` / `agent status` | ❌ Not built | `cli/commands/agent.py` not created |

### 🗂️ Missing test file

`tests/test_cli_map.py` does not exist.

### 🧹 Technical debt

| Location | Issue |
|---|---|
| `cli/rendering.py` | Dead code from an earlier `_visit()` function draft sits above the live `_render_node()` implementation |
| `backend/db/projects.py` | Excessive inline debug comments from a past bug fix (node_type/title swap) |
| `requirements.txt` | `sqlalchemy==2.0.37` is listed but never imported or used anywhere |
| `docs/DOCS_BACKEND.md`, `docs/DOCS_AI_CORE.md`, `docs/DOCS_FRONTEND.md` | Written for an abandoned Rust/Tauri architecture; describe a completely different tech stack |
| `backend/api/routers/agent.py` | `depth` field on `ResearchRequest` is accepted but silently ignored |

---

## 8. How to Use It Today

### Start the API

```bash
uvicorn backend.api.app:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Use the CLI (old flat commands — currently the only working entry-point)

```bash
# Initialise the database
python cli/main.py db init

# Ingest a URL
python cli/main.py ingest url --url "https://example.com/article"

# Ingest a PDF
python cli/main.py ingest pdf --path ./paper.pdf

# Search
python cli/main.py db search --query "your query" --mode hybrid

# Run the AI researcher
python cli/main.py research --goal "Summarise advances in solid-state batteries"
```

### Use the new command groups directly (workaround until `main.py` is wired)

The new commands can be invoked by running their modules directly, but this is awkward and not the intended UX. The proper fix is to wire them into `cli/main.py` (see Section 7).

---

## 9. Next Course of Action

These tasks are ordered by priority and dependency.

### Step 1 — Fix the `draft edit` bug (5 min)

In `cli/commands/draft.py`, `draft_edit()`: change `update_node(conn, node.id)` to `update_node(conn, node.id, updated_at=int(time.time()))`.

### Step 2 — Wire the new commands into `cli/main.py` (30 min) — CRITICAL

Mount `project_app`, `library_app`, `map_app`, `draft_app` in `cli/main.py`. Remove (or keep as legacy) the old `db`, `scrape`, `ingest`, `research` commands per the Phase 13 plan in `implementation_plan.md`.

After this step, the full new TUI is usable end-to-end for the first time.

### Step 3 — Validate the wired CLI works (smoke test)

```bash
python cli/main.py project new "Test"
python cli/main.py library add https://en.wikipedia.org/wiki/LangGraph
python cli/main.py library search "LangGraph"
python cli/main.py map show
python cli/main.py draft new "Notes"
```

### Step 4 — Write `tests/test_cli_map.py` (1–2 hrs)

The `map show` and `map connect` commands have no test coverage.

### Step 5 — Build `cli/commands/agent.py` (Phase 12, 2–3 hrs)

Wrap the existing `run_research()` in a project-aware CLI command that auto-links the result artifact to the active project. Also requires adding `artifact_id` to `ResearchState` in `backend/agent/state.py` so the runner surfaces the created node ID.

### Step 6 — Build `backend/rag/recall.py` + `library recall` command (Phase 9 completion, 2–3 hrs)

A RAG-based Q&A endpoint scoped to the active project. The search infrastructure is already fully in place — this is a thin LLM wrapper on top.

### Step 7 — Clean up code quality issues

- Remove dead `_visit()` code from `cli/rendering.py`
- Trim debug comments from `backend/db/projects.py`
- Remove `sqlalchemy` from `requirements.txt`

### Step 8 — Update documentation (1 hr)

Replace `docs/DOCS_BACKEND.md` and `docs/DOCS_AI_CORE.md` with accurate descriptions of the Python/FastAPI/LangGraph implementation. Archive or delete `docs/DOCS_FRONTEND.md`.

---

## 10. Phase Completion Status

| Phase | Description | Status |
|---|---|---|
| 0–5 | Backend (DB, scraper, RAG, agent, API) | ✅ Complete |
| 6 | State management / `CliContext` | ✅ Complete |
| 7 | Graph-scoping helpers (`projects.py`) | ✅ Complete |
| 8 | `project` command group | ✅ Complete |
| 9 | `library` command group | ⚠️ Partial — `recall` missing |
| 10 | `map` command group | ⚠️ Partial — `cluster` missing, no tests |
| 11 | `draft` command group | ⚠️ Partial — `attach` missing, `edit` bug |
| 12 | `agent` command group | ❌ Not started |
| 13 | CLI restructure / wiring | ❌ Not started — blocks full usability |
