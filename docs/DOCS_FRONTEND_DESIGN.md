# Re:Search — Frontend Design Specification

## 1. Paradigm Decision

**Chosen stack: Vite + React (TypeScript)**

Rationale:
- Fastest iteration path — standard React ecosystem, no native build step.
- Browser-based: works from any machine that can reach the FastAPI backend.
- Tauri wrapper can be added later for desktop packaging without code changes.
- React Flow provides a ready-made graph canvas for the `MapScreen`.

Alternatives considered:
| Option | Verdict |
|---|---|
| Tauri + React | Deferred — adds compile complexity before the UI is proven |
| Textual (TUI) | Limited graph rendering; CLI already covers this use-case |
| Next.js | Server-side rendering unnecessary for a local research tool |

---

## 2. Full API Surface Audit

All calls go to `http://localhost:8000` (dev). CORS is enabled on the backend.

### Projects
| Method | Path | Screen(s) |
|---|---|---|
| `GET` | `/projects` | `ProjectSwitcher` sidebar |
| `POST` | `/projects` | `ProjectSwitcher` — new project modal |
| `GET` | `/projects/{id}` | `ProjectSwitcher` — active project badge |
| `GET` | `/projects/{id}/nodes` | `LibraryScreen`, `MapScreen` |
| `GET` | `/projects/{id}/graph` | `MapScreen` canvas |
| `POST` | `/projects/{id}/link` | `LibraryScreen` — after ingest |
| `GET` | `/projects/{id}/export` | `ProjectSwitcher` — export button |

### Library / Ingest
| Method | Path | Screen(s) |
|---|---|---|
| `POST` | `/ingest/url` | `LibraryScreen` — add URL |
| `POST` | `/ingest/pdf` | `LibraryScreen` — upload PDF |
| `GET` | `/search?q=&mode=` | `LibraryScreen` — search bar |

### Nodes
| Method | Path | Screen(s) |
|---|---|---|
| `GET` | `/nodes` | `DraftsScreen` — artifact list |
| `POST` | `/nodes` | `DraftsScreen` — new draft |
| `GET` | `/nodes/{id}` | `DraftsScreen` — editor panel |
| `PUT` | `/nodes/{id}` | `DraftsScreen` — save |
| `DELETE` | `/nodes/{id}` | `DraftsScreen` — delete |
| `GET` | `/nodes/{id}/edges` | `MapScreen` — node detail panel |
| `GET` | `/nodes/graph/all` | `MapScreen` — global graph fallback |

### Research Agent
| Method | Path | Screen(s) |
|---|---|---|
| `POST` | `/research` | `AgentScreen` — SSE stream |

---

## 3. Screen Map

### 3.1 `ProjectSwitcher` (sidebar — always visible)

**API calls:** `GET /projects`, `POST /projects`, `GET /projects/{id}`

Responsibilities:
- Show active project name + a dropdown to switch.
- "+ New Project" button opens an inline modal.
- "Export" icon calls `GET /projects/{id}/export` and triggers a JSON download.

### 3.2 `LibraryScreen`

**API calls:** `POST /ingest/url`, `POST /ingest/pdf`, `GET /search`, `GET /projects/{id}/nodes`, `POST /projects/{id}/link`

Responsibilities:
- Input box with "Add URL" / "Upload PDF" tabs.
- On ingest success, call `POST /projects/{id}/link` to scope the new node.
- Search bar with mode selector (`fuzzy | semantic | hybrid`).
- Results list: node title, type badge, snippet, link to `DraftsScreen` if Artifact.

### 3.3 `MapScreen`

**API calls:** `GET /projects/{id}/graph`

Responsibilities:
- React Flow canvas rendering the project subgraph.
- Nodes displayed with type-specific icons; edges labelled with `relation_type`.
- Click a node → side panel with title, metadata, link to source/draft.
- "Suggest clusters" button calls the `map cluster` logic (future: expose via API).

### 3.4 `DraftsScreen`

**API calls:** `GET /nodes?type=Artifact`, `POST /nodes`, `GET /nodes/{id}`, `PUT /nodes/{id}`, `DELETE /nodes/{id}`

Responsibilities:
- Left panel: list of Artifact nodes scoped to the active project.
- Right panel: inline Markdown editor (e.g. TipTap or CodeMirror) for the selected draft.
- "New Draft" button → `POST /nodes` with `node_type="Artifact"`.
- Auto-save on blur / `Ctrl+S` → `PUT /nodes/{id}`.

### 3.5 `AgentScreen`

**API calls:** `POST /research` (SSE stream)

Responsibilities:
- Goal input + "Research" button.
- Depth selector: `quick | standard | deep`.
- Live progress feed parsed from SSE events:
  - `{"event":"node", "node":"planner", ...}` → progress step row.
  - `{"event":"done", "report":"..."}` → render final Markdown report.
  - `{"event":"error", "detail":"..."}` → error banner.
- "View in Map" button links to `MapScreen` after completion.

> **SSE note:** Use the browser's `EventSource` API. Verify `Content-Type: text/event-stream` and that CORS headers propagate through the stream before building this screen.

---

## 4. State Management

- **Active project ID** stored in React Context + Zustand store (`useProjectStore`).
  - Mirrors `~/.research_cli/context.json` from the CLI.
  - Persisted to `localStorage` under the key `researchActiveProjectId`.
- **Server state** (node lists, graph data) managed by **TanStack Query** (React Query).
  - Cache invalidated on mutations (ingest, link, create-draft).
- **Draft editor content** is local component state until saved.

---

## 5. ASCII Wireframes

### ProjectSwitcher sidebar
```
┌──────────────────────────────┐
│ 📁 Solid-State Batteries  ▾  │
│ ─────────────────────────── │
│   Solid-State Batteries      │
│   Paris Research             │
│ ─────────────────────────── │
│  + New Project   ⬇ Export   │
└──────────────────────────────┘
```

### LibraryScreen
```
┌──────────────────────────────────────────────┐
│  Add Source                                  │
│  [ URL ▼ ] [ https://...                ] [Add]│
│                                              │
│  Search: [ solid-state batteries       ] [🔍]│
│          Mode: ○ fuzzy  ● hybrid  ○ semantic │
│                                              │
│  Results (8)                                 │
│  ┌──────────────────────────────────────┐   │
│  │ 📄 Wikipedia: Solid-state battery    │   │
│  │    "...lithium-ion alternative..."   │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │ 📄 ArXiv 2106.09685 – Electrolytes   │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### MapScreen
```
┌──────────────────────────────────────────────┐
│  Map — Solid-State Batteries     [Cluster?]  │
│  ┌────────────────────────────────────────┐  │
│  │          [📁 Project Root]             │  │
│  │         /       |        \             │  │
│  │  [📄 Wiki]  [📄 ArXiv]  [📝 Report]   │  │
│  │      |                               │  │
│  │  [🧩 Chunk]                           │  │
│  └────────────────────────────────────────┘  │
│  Selected: ArXiv 2106.09685                  │
│  Type: Source | Created: 2026-02-01          │
└──────────────────────────────────────────────┘
```

### DraftsScreen
```
┌────────────────┬──────────────────────────────┐
│ Drafts         │  Chapter 1 — Introduction    │
│ ─────────────  │  ─────────────────────────── │
│ 📝 Chapter 1   │                              │
│ 📝 Summary     │  # Chapter 1                 │
│ 📝 Outline     │                              │
│                │  Solid-state batteries are   │
│  + New Draft   │  a promising alternative...  │
│                │                              │
│                │               [Save ✓]       │
└────────────────┴──────────────────────────────┘
```

### AgentScreen
```
┌──────────────────────────────────────────────┐
│  Agent Research                              │
│                                              │
│  Goal: [ Summarise solid-state batteries ] │
│  Depth: ○ quick  ● standard  ○ deep         │
│                           [ Run Research ]  │
│                                              │
│  Progress                                    │
│  ✅ planner    — queries drafted             │
│  ✅ searcher   — 6 URLs found                │
│  ⏳ scraper   — ingesting sources...         │
│  ○  synthesiser                              │
│                                              │
│  ─────────────────────────────────────────  │
│  ## Report                                   │
│  Solid-state batteries offer higher energy  │
│  density than conventional lithium-ion...   │
│               [ View in Map → ]              │
└──────────────────────────────────────────────┘
```
