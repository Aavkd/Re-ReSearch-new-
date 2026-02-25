# Re:Search

AI researcher agent with a Universal Node/Edge knowledge graph, RAG ingestion pipeline, autonomous LangGraph agent, and a React browser frontend.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify scaffold
python -c "import backend; print('scaffold ok')"
python cli/main.py --help
```

## Project Structure

```
Search/
├── docs/                    # Design documentation
├── backend/
│   ├── config.py            # Centralised settings (env-driven)
│   ├── db/                  # Phase 1: SQLite + FTS5 + sqlite-vec
│   ├── scraper/             # Phase 2: httpx + trafilatura + playwright
│   ├── rag/                 # Phase 3: chunker + embedder + ingestor
│   ├── agent/               # Phase 4: LangGraph researcher graph
│   └── api/                 # Phase 5: FastAPI HTTP layer
├── cli/
│   └── main.py              # Typer CLI entry-point
├── frontend/                # React + Vite browser frontend (F0–F8)
│   ├── src/
│   │   ├── api/             # axios API client (F1)
│   │   ├── types/           # Shared TypeScript types (F1)
│   │   ├── stores/          # Zustand state (F2)
│   │   ├── hooks/           # TanStack Query hooks (F2)
│   │   ├── components/      # UI components (F3–F8)
│   │   └── screens/         # Top-level screen components (F5–F8)
│   ├── package.json
│   └── vite.config.ts
├── tests/                   # pytest test suite
├── requirements.txt
└── pyproject.toml
```

## Frontend Quick Start

```bash
# Requires Node.js ≥ 18 and the backend running on http://localhost:8000
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # production bundle → frontend/dist/
npm run test       # vitest unit tests
```

## Configuration

Copy `.env.example` (if provided) to `.env` and set:

| Variable | Default | Description |
|---|---|---|
| `RESEARCH_WORKSPACE` | `~/.research_data` | Directory for the SQLite DB |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma:latest` | Embedding model |
| `OLLAMA_CHAT_MODEL` | `ministral-3:8b` | Chat/reasoning model |
| `OPENAI_API_KEY` | _(unset)_ | Required if using OpenAI |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Build Phases

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Project scaffold |
| 1 | ✅ Complete | Database layer (SQLite + FTS5 + sqlite-vec) |
| 2 | ✅ Complete | Web scraper (httpx + trafilatura + Playwright) |
| 3 | ✅ Complete | RAG ingestion pipeline |
| 4 | ✅ Complete | LangGraph researcher agent |
| 5 | ✅ Complete | FastAPI HTTP layer |
| 6 | ✅ Complete | CLI state management (`cli/context.py`) |
| 7 | ✅ Complete | Backend graph-scoping helpers (`backend/db/projects.py`) |
| 8 | ✅ Complete | `project` command group |
| 9 | ✅ Complete | `library` command group (add, list, search, recall) |
| 10 | ✅ Complete | `map` command group (show, connect, cluster) |
| 11 | ✅ Complete | `draft` command group (new, list, show, edit, attach) |
| 12 | ✅ Complete | `agent` command group |
| 13 | ✅ Complete | CLI restructure & cleanup |
| 14 | ✅ Complete | API hardening — CORS + `/projects` REST endpoints |

### Frontend Phases

| Phase | Status | Description |
|---|---|---|
| F0 | ✅ Complete | Vite + React + TypeScript scaffold, Tailwind, Vitest |
| F1 | ✅ Complete | TypeScript types, axios API client, SSE agent helper, unit tests |
| F2 | ✅ Complete | Zustand project store, TanStack Query hooks |
| F3 | ✅ Complete | App shell, sidebar, routing skeleton |
| F4 | 🔲 Planned | `ProjectSwitcher` component |
| F5 | 🔲 Planned | `LibraryScreen` (ingest + search) |
| F6 | 🔲 Planned | `MapScreen` (React Flow graph canvas) |
| F7 | 🔲 Planned | `DraftsScreen` (CodeMirror Markdown editor) |
| F8 | 🔲 Planned | `AgentScreen` (SSE progress + report) |

## CLI Commands

> **Note:** the new command groups are wired in Phase 13. Until then, run them directly against their sub-apps during development.

### `project` — workspace lifecycle

```bash
python cli/main.py project new "My Project"
python cli/main.py project list
python cli/main.py project switch "My Project"
python cli/main.py project status
python cli/main.py project export
```

### `library` — ingest and search sources

```bash
python cli/main.py library add "https://example.com/article"
python cli/main.py library add "/path/to/paper.pdf"
python cli/main.py library list
python cli/main.py library search "solid-state batteries" --mode hybrid
python cli/main.py library search "topic" --global        # search all projects
python cli/main.py library recall "What are the main findings?"
```

### `map` — visualise and connect the knowledge graph

```bash
python cli/main.py map show                               # ASCII tree (default)
python cli/main.py map show --format list                 # flat list
python cli/main.py map connect <node_a_id> <node_b_id> --label CITES
python cli/main.py map cluster                            # LLM-suggested edges
python cli/main.py map cluster --apply                    # auto-create edges
```

### `draft` — create and edit artifact documents

```bash
python cli/main.py draft new "Chapter 1"
python cli/main.py draft list
python cli/main.py draft show <node_id>
python cli/main.py draft edit <node_id>                   # opens $EDITOR
python cli/main.py draft attach <artifact_id> <source_id>  # CITES edge
```

### `agent` — delegated research

```bash
python cli/main.py agent hire --goal "Summarise solid-state battery progress"
python cli/main.py agent hire --goal "..." --depth deep
python cli/main.py agent status                           # list agent-produced reports
```

## API Server

Start the server:

```bash
uvicorn backend.api.app:app --reload
```

Interactive docs: `http://localhost:8000/docs`

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/nodes` | Create a graph node |
| `GET` | `/nodes` | List nodes (`?type=` filter) |
| `GET` | `/nodes/graph/all` | All nodes + edges |
| `GET` | `/nodes/{id}` | Get a single node |
| `PUT` | `/nodes/{id}` | Update a node |
| `DELETE` | `/nodes/{id}` | Delete a node |
| `GET` | `/nodes/{id}/edges` | Edges for a node |
| `GET` | `/search?q=...&mode=fuzzy\|semantic\|hybrid` | Knowledge-base search |
| `POST` | `/ingest/url` | Body `{"url":"..."}` → scrape + ingest |
| `POST` | `/ingest/pdf` | Multipart PDF → ingest |
| `POST` | `/research` | Body `{"goal":"..."}` → SSE research stream |
| `GET` | `/projects` | List all Project nodes |
| `POST` | `/projects` | Create a new Project |
| `GET` | `/projects/{id}` | Project summary (node/edge counts, recent artifacts) |
| `GET` | `/projects/{id}/nodes` | All nodes in project (BFS depth, default 2) |
| `GET` | `/projects/{id}/graph` | Subgraph (nodes + edges) for canvas rendering |
| `POST` | `/projects/{id}/link` | Body `{"node_id":"...","relation":"..."}` → link node to project |
| `GET` | `/projects/{id}/export` | Full subgraph as JSON |

> **CORS:** The API accepts requests from any origin (`Access-Control-Allow-Origin: *`). Tighten `allow_origins` in `backend/api/app.py` before deploying to production.
