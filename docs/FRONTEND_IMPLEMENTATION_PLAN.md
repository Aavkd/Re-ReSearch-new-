# Re:Search — Frontend Implementation Plan

## Overview

Build a browser-based React frontend for the Re:Search app inside a new `frontend/` directory at the workspace root. The backend (FastAPI, `localhost:8000`) is complete and requires no new endpoints. CORS is already enabled for all origins.

**Tech stack:**
| Concern | Library |
|---|---|
| Build tool | Vite 5 |
| UI framework | React 18 + TypeScript |
| Routing | React Router v6 |
| Server state | TanStack Query v5 (React Query) |
| Client state | Zustand v4 |
| Graph canvas | React Flow v12 |
| Markdown editor | CodeMirror 6 (with `@codemirror/lang-markdown`) |
| Markdown render | `react-markdown` + `remark-gfm` |
| Styling | Tailwind CSS v3 |
| HTTP client | `axios` (thin wrapper) |
| SSE | Native `EventSource` API |
| Testing | Vitest + React Testing Library |
| E2E (optional) | Playwright |

---

## Implementation Notes (Phases F0 & F1 — completed Feb 2026)

### F0 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| TS config files | `tsconfig.json` (browser) + `tsconfig.node.json` (Vite) | Added `tsconfig.app.json` for the browser target; `tsconfig.json` is a project-references root. This matches the Vite 5 scaffold default and is required for `tsc -b`. |
| `vite.config.ts` import | `import { defineConfig } from "vite"` | Uses `import { defineConfig } from "vitest/config"` so the `test:` block is correctly typed by Vitest. |
| `npm run test` | `vitest run` | `vitest run --passWithNoTests` — vitest exits 1 with no test files by default; this flag satisfies the "0 tests, 0 failures" validation requirement. |

### F1 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| `ProjectSummary.recent_artifacts` | `ArtifactNode[]` | `string[]` — the backend (`db/projects.py::get_project_summary`) appends `n.title` strings, not full node objects. The TypeScript type matches the actual API. Add a `// TODO` comment tracks the discrepancy. Update to `ArtifactNode[]` if the backend changes. |
| SSE transport note | "Native `EventSource` API" in tech stack | The `/research` endpoint is a POST, so `EventSource` (GET-only) cannot be used. `api/agent.ts` uses `fetch` + `AbortController` + `ReadableStream` as specified in the F1 implementation details. |

---

## Implementation Notes (Phases F2 & F3 — completed Feb 2026)

### F2 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| `useProjectSummary` signature | `id: string` | `id: string \| null` — callers get `activeProjectId` from Zustand which is `string \| null`; using `null` keeps the `enabled: !!id` guard consistent across all hooks. |
| `useCreateNode` / `useDeleteNode` invalidation | `['nodes']` only | Also invalidates `['projectGraph', activeProjectId]` when a project is active — this keeps the map canvas fresh after node creation without a manual refresh. |
| `App.tsx` providers | `<AppShell />` as single child | `ReactQueryDevtools` is rendered outside `BrowserRouter` (after `</BrowserRouter>`) and only when `import.meta.env.DEV` is true, so it never appears in production builds. |

### F3 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| `AppShell` includes `<ProjectSwitcher />` | Rendered inside sidebar | A clearly-labelled placeholder `<div data-testid="project-switcher-slot">` is used instead; the real component is wired in Phase F4. |
| Redirect at index route | Implicit behaviour | Explicit `<Navigate to="/library" replace />` at the index route ensures the redirect is visible and testable without actual navigation history manipulation. |
| React Router v6 future flags | Not mentioned | Two `v7_*` future-flag console warnings appear in test output (informational only, not failures). These can be silenced by passing `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}` to `<BrowserRouter>` when upgrading to React Router v7. |

---

## Implementation Notes (Phases F4 & F5 — completed Feb 2026)

### F4 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| `AppShell` placeholder slot | `data-testid="project-switcher-slot"` removed | The wrapper `<div data-testid="project-switcher-slot">` is retained around `<ProjectSwitcher />` so the existing AppShell test continues to pass. |
| `useProjectSummary` not used in `ProjectSwitcher` | Not specified | `ProjectSwitcher` only needs the flat list from `useProjectList`; summary stats are not needed for the switcher UI. |
| `URL.createObjectURL` in export | Standard browser API | jsdom does not implement `URL.createObjectURL`; the export test assigns it as a `vi.fn()` mock directly on the `URL` global before asserting. |

### F5 — Deviations from plan

| Item | Plan | Actual |
|---|---|---|
| `useProjectNodes` hook | Not listed in F2 hooks | Added to `hooks/useProjects.ts` so `LibraryScreen` can load project-scoped nodes without a new file. |
| Debounce test strategy | "Only one query fired after 300 ms" using fake timers | `vi.useFakeTimers()` blocks MSW response resolution in vitest 3.x. Tests use real timers: three rapid `fireEvent.change` calls are fired synchronously, then `waitFor` (2 s timeout) verifies only one search request was made — which holds because the debounce fires once after the last change. |
| `SearchBar` debounce implementation | `useDebounce` hook or utils file | Debounce is implemented inline in `SearchBar.tsx` via `useEffect` + `useRef` for a stable `onChange` reference. No separate utility file is needed. |
| Search result scoping | Server-side project filter param | `GET /search` has no `project_id` param. `LibraryScreen` fetches `GET /projects/{id}/nodes` for the empty-query list and filters search results client-side by the project's node id set. Tracked by a `// TODO` comment. |

---

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tailwind.config.ts
├── postcss.config.js
├── package.json
├── .env.development          # VITE_API_BASE_URL=http://localhost:8000
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx              # React root mount
    ├── App.tsx               # Router + QueryClient + Zustand providers
    ├── api/
    │   ├── client.ts         # axios instance, base URL from env
    │   ├── projects.ts       # project API calls
    │   ├── library.ts        # ingest + search API calls
    │   ├── nodes.ts          # node CRUD API calls
    │   └── agent.ts          # SSE research stream helper
    ├── stores/
    │   └── projectStore.ts   # Zustand: activeProjectId, setActiveProject
    ├── types/
    │   └── index.ts          # Shared TS interfaces (Node, Edge, Project, etc.)
    ├── hooks/
    │   ├── useProjects.ts    # TanStack Query wrappers for /projects
    │   ├── useProjectGraph.ts# TanStack Query wrapper for /projects/{id}/graph
    │   ├── useNodes.ts       # TanStack Query wrappers for /nodes
    │   └── useSearch.ts      # TanStack Query wrapper for /search
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx        # Sidebar + main content area
    │   │   └── NavBar.tsx          # Top nav bar (screen switcher)
    │   ├── sidebar/
    │   │   ├── ProjectSwitcher.tsx # Dropdown + new project modal
    │   │   └── NewProjectModal.tsx # Controlled form modal
    │   ├── library/
    │   │   ├── AddSourcePanel.tsx  # URL / PDF tabs + submit
    │   │   ├── SearchBar.tsx       # Query input + mode selector
    │   │   └── NodeResultCard.tsx  # Single search result row
    │   ├── map/
    │   │   ├── GraphCanvas.tsx     # React Flow wrapper
    │   │   ├── NodeDetailPanel.tsx # Slide-in panel for selected node
    │   │   └── customNodes/
    │   │       ├── SourceNode.tsx
    │   │       ├── ArtifactNode.tsx
    │   │       └── ProjectNode.tsx
    │   ├── drafts/
    │   │   ├── DraftList.tsx       # Left-panel artifact list
    │   │   ├── DraftEditor.tsx     # CodeMirror markdown editor
    │   │   └── NewDraftModal.tsx
    │   └── agent/
    │       ├── GoalForm.tsx        # Goal input + depth selector
    │       ├── ProgressFeed.tsx    # SSE event rows
    │       └── ReportPanel.tsx     # Final rendered markdown report
    └── screens/
        ├── LibraryScreen.tsx
        ├── MapScreen.tsx
        ├── DraftsScreen.tsx
        └── AgentScreen.tsx
```

---

## Phase F0 — Scaffold & Toolchain

**Goal:** A working Vite + React + TypeScript project in `frontend/` that renders "Hello Re:Search" in the browser.

**No dependencies on other phases.**

### Files to Create

| File | Purpose |
|---|---|
| `frontend/package.json` | NPM manifest with all dependencies pre-declared |
| `frontend/vite.config.ts` | Vite config — server proxy for `/api` → `localhost:8000` during dev |
| `frontend/tsconfig.json` | TypeScript config for the browser bundle |
| `frontend/tsconfig.node.json` | TypeScript config for Vite config file |
| `frontend/tailwind.config.ts` | Tailwind config pointing at `src/**/*.{ts,tsx}` |
| `frontend/postcss.config.js` | PostCSS with `tailwindcss` and `autoprefixer` |
| `frontend/index.html` | HTML entry — `<div id="root">` + `<script src="/src/main.tsx">` |
| `frontend/.env.development` | `VITE_API_BASE_URL=http://localhost:8000` |
| `frontend/src/main.tsx` | Mount `<App />` into `#root` with `StrictMode` |
| `frontend/src/App.tsx` | Placeholder: renders `<h1>Hello Re:Search</h1>` |

### `package.json` Dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "axios": "^1.7.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-flow-renderer": "^10.3.17",
    "reactflow": "^11.11.0",
    "react-markdown": "^9.0.0",
    "react-router-dom": "^6.26.0",
    "remark-gfm": "^4.0.0",
    "zustand": "^4.5.0",
    "@codemirror/lang-markdown": "^6.2.0",
    "@codemirror/view": "^6.0.0",
    "@codemirror/state": "^6.0.0",
    "codemirror": "^6.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "@vitest/coverage-v8": "^1.6.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.4.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^24.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0"
  }
}
```

### `vite.config.ts` Key Settings

- `plugins: [react()]`
- `server.proxy`: proxy `/api` → `http://localhost:8000` (strips `/api` prefix). This avoids CORS in dev and matches the CORS wildcard already configured.
- `test.environment: "jsdom"` — enables Vitest browser simulation.
- `test.setupFiles: ["src/test-setup.ts"]` — imports `@testing-library/jest-dom`.

### Validation

```bash
cd frontend
npm install
npm run dev
# Browser at http://localhost:5173 shows "Hello Re:Search"
npm run build      # zero TypeScript errors, no dead imports
npm run test       # 0 tests, 0 failures (empty suite passes)
```

---

## Phase F1 — Type Definitions & API Client

**Goal:** Define all shared TypeScript interfaces and the axios-based HTTP client so every subsequent phase can import them without re-defining shapes.

**Depends on:** Phase F0 (project initialised).

### Files to Create

#### `frontend/src/types/index.ts`

Define the following interfaces, mirroring the backend's serialisation helpers exactly:

```typescript
export interface ProjectNode {
  id: string;
  node_type: "Project";
  title: string;
  content_path: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SourceNode {
  id: string;
  node_type: "Source" | "Chunk";
  title: string;
  content_path: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ArtifactNode {
  id: string;
  node_type: "Artifact";
  title: string;
  content_path: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type AppNode = ProjectNode | SourceNode | ArtifactNode;

export interface Edge {
  source_id: string;
  target_id: string;
  relation_type: string;
  created_at: string;
}

export interface ProjectGraph {
  nodes: AppNode[];
  edges: Edge[];
}

export interface ProjectSummary {
  project_id: string;
  node_counts: Record<string, number>;
  edge_count: number;
  recent_artifacts: ArtifactNode[];
}

export interface IngestResponse {
  node_id: string;
  title: string;
  node_type: string;
  metadata: Record<string, unknown>;
}

export type SearchMode = "fuzzy" | "semantic" | "hybrid";

export type ResearchDepth = "quick" | "standard" | "deep";

export interface SseNodeEvent {
  event: "node";
  node: string;
  status: string;
  [key: string]: unknown;
}

export interface SseDoneEvent {
  event: "done";
  report: string;
  artifact_id: string;
}

export interface SseErrorEvent {
  event: "error";
  detail: string;
}

export type SseEvent = SseNodeEvent | SseDoneEvent | SseErrorEvent;
```

#### `frontend/src/api/client.ts`

- Create a named axios instance with `baseURL` read from `import.meta.env.VITE_API_BASE_URL`.
- Export it as `apiClient`.
- Add a response interceptor that normalises HTTP error status codes into thrown `Error` objects with a human-readable message (`error.response.data.detail` when available).

#### `frontend/src/api/projects.ts`

Functions:
- `fetchProjects(): Promise<AppNode[]>` — `GET /projects`
- `createProject(name: string): Promise<AppNode>` — `POST /projects`
- `fetchProjectSummary(id: string): Promise<ProjectSummary>` — `GET /projects/{id}`
- `fetchProjectNodes(id: string, depth?: number): Promise<AppNode[]>` — `GET /projects/{id}/nodes`
- `fetchProjectGraph(id: string): Promise<ProjectGraph>` — `GET /projects/{id}/graph`
- `linkNodeToProject(projectId: string, nodeId: string, relation?: string): Promise<void>` — `POST /projects/{id}/link`
- `exportProject(id: string): Promise<unknown>` — `GET /projects/{id}/export`

#### `frontend/src/api/library.ts`

- `ingestUrl(url: string): Promise<IngestResponse>` — `POST /ingest/url`
- `ingestPdf(file: File): Promise<IngestResponse>` — `POST /ingest/pdf` (multipart using `FormData`)
- `search(query: string, mode?: SearchMode, topK?: number): Promise<AppNode[]>` — `GET /search?q=...&mode=...&top_k=...`

#### `frontend/src/api/nodes.ts`

- `fetchNodes(type?: string): Promise<AppNode[]>` — `GET /nodes?type=...`
- `fetchNode(id: string): Promise<AppNode>` — `GET /nodes/{id}`
- `createNode(payload: Partial<AppNode>): Promise<AppNode>` — `POST /nodes`
- `updateNode(id: string, payload: Partial<AppNode>): Promise<AppNode>` — `PUT /nodes/{id}`
- `deleteNode(id: string): Promise<void>` — `DELETE /nodes/{id}`

#### `frontend/src/api/agent.ts`

- `streamResearch(goal: string, depth: ResearchDepth, onEvent: (e: SseEvent) => void, onDone: () => void, onError: (e: Error) => void): () => void`
  - Opens `POST /research` via `fetch()` with `Accept: text/event-stream`.
  - Parses the `ReadableStream` manually (the `EventSource` API requires GET; POST needs the Fetch Streams API).
  - Returns a cleanup function that aborts the fetch.
  - Each `data:` line is JSON-parsed and dispatched to `onEvent`.
  - Returns the abort function for React `useEffect` cleanup.

> **Implementation note:** Use `fetch` with `AbortController` rather than `EventSource` because the `/research` endpoint is a POST. Parse the response body as a `ReadableStream<Uint8Array>`, decode with `TextDecoder`, split on `\n\n`, and extract `data:` lines.

### Tests to Write

File: `frontend/src/api/__tests__/client.test.ts`

| Test | Assertion |
|---|---|
| `normalises 404 detail` | Interceptor extracts `detail` from FastAPI error response |
| `normalises network error` | Throws `Error` with message "Network Error" |

File: `frontend/src/api/__tests__/projects.test.ts`

Use `vi.mock('axios')` / `msw` handlers — mock all HTTP at the network level.

| Test | Assertion |
|---|---|
| `fetchProjects returns array` | Parses response body into `AppNode[]` |
| `createProject posts correct body` | `POST /projects` body is `{name: "Test"}` |
| `linkNodeToProject posts correct body` | Body is `{node_id, relation}` |

### Validation

```bash
npm run test src/api
# All API unit tests pass
npm run build
# TypeScript compiles cleanly
```

---

## Phase F2 — State Management

**Goal:** Implement the Zustand store for active project and connect it to React Query's QueryClient.

**Depends on:** F1 (types and API client).

### Files to Create

#### `frontend/src/stores/projectStore.ts`

Zustand store with:

```typescript
interface ProjectStore {
  activeProjectId: string | null;
  activeProjectName: string | null;
  setActiveProject: (id: string, name: string) => void;
  clearActiveProject: () => void;
}
```

- **Persistence:** Use Zustand's `persist` middleware, backing to `localStorage` under the key `researchActiveProject`.
- Shape stored: `{ activeProjectId, activeProjectName }`.

#### `frontend/src/hooks/useProjects.ts`

TanStack Query wrappers:

- `useProjectList()` — `useQuery({ queryKey: ['projects'], queryFn: fetchProjects })` — staleTime 60 s.
- `useCreateProject()` — `useMutation` that calls `createProject`, then invalidates `['projects']`.
- `useProjectSummary(id)` — `useQuery({ queryKey: ['project', id], queryFn: () => fetchProjectSummary(id), enabled: !!id })`.

#### `frontend/src/hooks/useProjectGraph.ts`

- `useProjectGraph(id)` — `useQuery({ queryKey: ['projectGraph', id], queryFn: () => fetchProjectGraph(id), enabled: !!id, staleTime: 30_000 })`.

#### `frontend/src/hooks/useNodes.ts`

- `useNodeList(type?)` — `useQuery` on `fetchNodes(type)`.
- `useNode(id)` — `useQuery` on `fetchNode(id)`.
- `useCreateNode()` — `useMutation` + invalidate `['nodes']` + invalidate `['projectGraph', activeProjectId]`.
- `useUpdateNode()` — `useMutation` + invalidate specific `['node', id]`.
- `useDeleteNode()` — `useMutation` + invalidate `['nodes']`.

#### `frontend/src/hooks/useSearch.ts`

- `useSearch(query, mode, topK)` — `useQuery({ queryKey: ['search', query, mode, topK], queryFn: ... , enabled: query.length > 1, staleTime: 0 })`.

#### `frontend/src/App.tsx` (rewrite from F0 placeholder)

Wrap the React tree with:
1. `<QueryClientProvider client={queryClient}>` — `queryClient` created with `new QueryClient()` at module level.
2. `<ReactQueryDevtools />` in development.
3. `<BrowserRouter>` from React Router.
4. `<AppShell />` (created in F3) as the single child.

### Tests to Write

File: `frontend/src/stores/__tests__/projectStore.test.ts`

| Test | Assertion |
|---|---|
| `initial state is null` | `activeProjectId` is `null` on fresh store |
| `setActiveProject updates both fields` | `id` and `name` both stored |
| `persists to localStorage` | After `setActiveProject`, `localStorage` key has correct JSON |
| `clearActiveProject resets to null` | Both fields become `null` after clear |

File: `frontend/src/hooks/__tests__/useProjects.test.tsx`

Use `renderWithProviders` helper that wraps in `QueryClientProvider` with a fresh client.

| Test | Assertion |
|---|---|
| `useProjectList fetches on mount` | Calls `GET /projects` once |
| `useCreateProject invalidates list` | After mutation, `['projects']` query is re-fetched |

### Validation

```bash
npm run test src/stores src/hooks
```

---

## Phase F3 — App Shell & Routing

**Goal:** Create the navigable skeleton — sidebar, nav bar, and screen routing — so each screen can be developed in isolation.

**Depends on:** F2 (store ready), F0 (Tailwind set up).

### Files to Create

#### `frontend/src/components/layout/AppShell.tsx`

Two-column layout:

```
┌─────────────────────────────────────────────┐
│  [Sidebar: ProjectSwitcher]  [Main content] │
│  Fixed left, 280px            Flex fill     │
└─────────────────────────────────────────────┘
```

- Left column (fixed, `w-64`): renders `<ProjectSwitcher />` at the top, `<NavBar />` below it.
- Right column (fills remaining): `<Outlet />` from React Router renders the active screen.
- The sidebar scrolls independently; the main content area also scrolls independently.

#### `frontend/src/components/layout/NavBar.tsx`

Vertical list of navigation links using `<NavLink>` from React Router:

| Label | Route |
|---|---|
| Library | `/library` |
| Map | `/map` |
| Drafts | `/drafts` |
| Agent | `/agent` |

Active link gets a highlighted background (Tailwind `bg-blue-100 text-blue-800`). Inactive uses `text-gray-600 hover:bg-gray-100`.

#### `frontend/src/App.tsx` (update from F2)

Replace placeholder content with `<Routes>`:

```tsx
<Routes>
  <Route path="/" element={<AppShell />}>
    <Route index element={<Navigate to="/library" replace />} />
    <Route path="library" element={<LibraryScreen />} />
    <Route path="map" element={<MapScreen />} />
    <Route path="drafts" element={<DraftsScreen />} />
    <Route path="drafts/:nodeId" element={<DraftsScreen />} />
    <Route path="agent" element={<AgentScreen />} />
  </Route>
</Routes>
```

Each screen component starts as a stub: `<div>LibraryScreen placeholder</div>`. These are replaced in later phases.

### Tests to Write

File: `frontend/src/components/layout/__tests__/AppShell.test.tsx`

| Test | Assertion |
|---|---|
| `renders sidebar` | `ProjectSwitcher` is present in the DOM |
| `renders nav links` | All 4 nav links are present |
| `active route highlights link` | Library link has active class at `/library` |
| `redirects root to /library` | Visiting `/` redirects to `/library` |

### Validation

```bash
npm run dev
# http://localhost:5173/library shows layout shell with nav + placeholder
npm run test src/components/layout
```

---

## Phase F4 — `ProjectSwitcher` Component

**Goal:** Sidebar component that shows the active project, allows switching, and can create a new project.

**Depends on:** F2 (store + `useProjects` hook), F3 (shell exists).

### Files to Create

#### `frontend/src/components/sidebar/ProjectSwitcher.tsx`

Behaviour:
1. Reads `activeProjectId` and `activeProjectName` from Zustand store.
2. Renders the active project name in a `<button>` that opens a dropdown.
3. Dropdown lists all projects from `useProjectList()`, each clickable.
4. On click: calls `setActiveProject(p.id, p.title)` and closes dropdown.
5. "+ New Project" button at the bottom of the dropdown opens `<NewProjectModal />`.
6. "Export ↓" button calls `exportProject(activeProjectId)` and triggers a JSON file download using a `Blob` + `URL.createObjectURL` pattern.
7. If no active project: shows "No project selected" greyed out.
8. Loading state: skeleton shimmer replaces project name.
9. Error state: shows "Failed to load projects" with a retry button.

#### `frontend/src/components/sidebar/NewProjectModal.tsx`

Controlled modal:
- Single text input: "Project name".
- "Create" button calls `useCreateProject()` mutation.
- On success: calls `setActiveProject` with the returned project, closes modal.
- Disabled state while mutation is pending.
- Escape key and backdrop click close the modal.
- Error message inline if mutation fails.

### Tests to Write

File: `frontend/src/components/sidebar/__tests__/ProjectSwitcher.test.tsx`

MSW (Mock Service Worker) handlers mock `GET /projects` and `POST /projects`.

| Test | Assertion |
|---|---|
| `shows active project name` | Zustand store name appears in button |
| `dropdown lists all projects` | Click button → all project titles visible |
| `selecting a project updates store` | `setActiveProject` called with correct id/name |
| `export button triggers download` | `URL.createObjectURL` called; anchor click fired |
| `new project modal opens` | Clicking "+ New Project" renders modal |
| `create project updates active` | After POST, store contains new project id |

### Validation

```bash
npm run test src/components/sidebar
# Manual: select and switch projects in the browser
```

---

## Phase F5 — `LibraryScreen`

**Goal:** The ingestion and search screen. Users add URLs or PDFs; search the knowledge base; see results scoped to the active project.

**Depends on:** F2 (hooks), F3 (routing), F4 (active project in store).

### Files to Create

#### `frontend/src/components/library/AddSourcePanel.tsx`

Two tabs: **URL** | **PDF**.

- **URL tab:** Text input + "Add" button. On submit, calls `ingestUrl(url)` then immediately calls `linkNodeToProject(activeProjectId, result.node_id)`. Shows a spinner during pending. Shows `✓ Added: {title}` or an inline error on failure.
- **PDF tab:** File input (`accept=".pdf"`). On file select, calls `ingestPdf(file)` then `linkNodeToProject`. Shows upload progress (indeterminate spinner; PDF endpoint is synchronous from the client's POV).
- After either ingest, invalidates `['projectGraph', activeProjectId]` and `['nodes']` query keys via the QueryClient.

#### `frontend/src/components/library/SearchBar.tsx`

- Controlled text input with a 300 ms debounce (use a `useDebounce` hook inline or imported from a `utils` file).
- Radio group for `mode`: fuzzy | hybrid | semantic.
- Passes `{ query, mode }` up via `onChange` callback props.

#### `frontend/src/components/library/NodeResultCard.tsx`

Props: `node: AppNode`.

- Displays: type badge (colour-coded: Source = blue, Artifact = green, Chunk = grey), title, snippet from `metadata.snippet` if present, creation date.
- Artifact nodes get a "→ Open Draft" link that navigates to `/drafts/{node.id}`.

#### `frontend/src/screens/LibraryScreen.tsx`

Assembles the sub-components:

```
┌─────────────────────────────────────────────┐
│  <AddSourcePanel />                         │
│  <SearchBar />                              │
│  {results.map(n => <NodeResultCard n={n} />}│
└─────────────────────────────────────────────┘
```

State:
- `query` and `mode` driven by `<SearchBar />` callbacks.
- `useSearch(query, mode)` hook drives results list (scoped search is handled by the backend's scope_ids but the current `/search` endpoint is global; note below).
- Shows "No results" empty state when query non-empty and list empty.
- Shows loading skeleton (3 ghost rows) while fetching.

> **Current API limitation:** `GET /search` does not accept a `project_id` filter — it searches all nodes. To scope search to the active project, fetch `GET /projects/{id}/nodes` and display that list when query is empty; when a query is active, filter the result list client-side by the project's node id set. This avoids a backend change. Document this in a `// TODO` comment.

### Tests to Write

File: `frontend/src/screens/__tests__/LibraryScreen.test.tsx`

| Test | Assertion |
|---|---|
| `renders add source panel` | URL input and PDF button visible |
| `ingest URL calls API then links` | `POST /ingest/url` then `POST /projects/{id}/link` |
| `search debounces input` | Only one query fired after 300 ms |
| `mode selector changes query param` | `mode=semantic` appears in GET request |
| `empty state shown on no results` | "No results" text visible |
| `artifact card links to drafts` | `<a href="/drafts/{id}">` present |
| `shows error on ingest failure` | Error message visible when API 502 |
| `requires active project for add` | Add button disabled when no project active |

### Validation

```bash
npm run test src/screens/__tests__/LibraryScreen.test.tsx
# Manual: add a URL, see it appear in results
```

---

## Phase F6 — `MapScreen`

**Goal:** Interactive graph canvas for the active project. Users can explore node relationships and click nodes for detail.

**Depends on:** F2 (`useProjectGraph`), F3 (routing), F4 (active project).

### Files to Create

#### `frontend/src/components/map/customNodes/ProjectNode.tsx`

React Flow custom node component for nodes with `node_type == "Project"`. Renders folder icon + title.

#### `frontend/src/components/map/customNodes/SourceNode.tsx`

Custom node for `Source` type. Document icon + title (truncated at 30 chars). Blue border.

#### `frontend/src/components/map/customNodes/ArtifactNode.tsx`

Custom node for `Artifact` type. Scroll icon + title. Green border.

#### `frontend/src/components/map/GraphCanvas.tsx`

Props:
```typescript
interface GraphCanvasProps {
  graphData: ProjectGraph;
  onNodeClick: (node: AppNode) => void;
}
```

Responsibilities:
1. Convert backend `graphData.nodes` to React Flow `Node[]`:
   - `id`: node `id`
   - `type`: one of `"projectNode" | "sourceNode" | "artifactNode"` based on `node_type`
   - `data`: `{ label: node.title, raw: node }`
   - Position: computed by React Flow's auto-layout (`dagre` algorithm via `@dagrejs/dagre` — add to dependencies). Layout is LR (left-to-right) if > 10 nodes, TB (top-bottom) otherwise.
2. Convert backend `graphData.edges` to React Flow `Edge[]`:
   - `id`: `${source_id}-${target_id}-${relation_type}`
   - `source`, `target`
   - `label`: `relation_type` (shown on hover)
   - `markerEnd`: arrow
3. Register custom node types: `{ projectNode: ProjectNode, sourceNode: SourceNode, artifactNode: ArtifactNode }`.
4. On node click: call `onNodeClick(node.data.raw)`.
5. Controls: zoom in/out (`<Controls />`), minimap (`<MiniMap />`), fit-view on data change.
6. Empty state: "No nodes in this project yet" centred message when `nodes` is empty.

> **Dependency to add:** `@dagrejs/dagre` for layout calculation. Install alongside `reactflow`.

#### `frontend/src/components/map/NodeDetailPanel.tsx`

Slide-in panel (right side, absolute positioned over map canvas).

Props:
```typescript
interface NodeDetailPanelProps {
  node: AppNode | null;
  onClose: () => void;
}
```

Displays:
- Title (heading)
- `node_type` badge
- `created_at` formatted as locale date string
- `metadata.url` as a clickable link (if present)
- "Open Draft" button (navigates to `/drafts/{id}`, shown only for Artifact nodes)
- Close (×) button

#### `frontend/src/screens/MapScreen.tsx`

State:
- `selectedNode: AppNode | null` — set when a node is clicked.

Structure:
```
┌──────────────────────────────────────────────┐
│  "Map — {project name}"  [Refresh ↺]        │
│  ┌────────────────────────────────────────┐  │
│  │  <GraphCanvas graphData={...}          │  │
│  │              onNodeClick={setSelected} │  │
│  └────────────────────────────────────────┘  │
│  <NodeDetailPanel node={selectedNode} ... /> │
└──────────────────────────────────────────────┘
```

- Uses `useProjectGraph(activeProjectId)`.
- Loading state: spinner centred in canvas area.
- No project selected: "Select a project to view its map."
- Error: "Failed to load graph. Retry?"

### Tests to Write

File: `frontend/src/components/map/__tests__/GraphCanvas.test.tsx`

| Test | Assertion |
|---|---|
| `renders nodes correctly` | Each node id appears in DOM |
| `empty state shown` | "No nodes" message when nodes=[] |
| `onNodeClick fires` | Callback called with correct node |

File: `frontend/src/components/map/__tests__/NodeDetailPanel.test.tsx`

| Test | Assertion |
|---|---|
| `renders null gracefully` | Nothing renders when node=null |
| `shows node title and type` | Title and badge visible |
| `shows URL link for Source` | `<a>` tag rendered with metadata.url |
| `hides draft link for Source` | "Open Draft" not visible for Source node |
| `shows draft link for Artifact` | "Open Draft" link present for Artifact node |
| `onClose fires on × click` | Callback invoked |

### Validation

```bash
npm run test src/components/map src/screens/__tests__/MapScreen.test.tsx
# Manual: MapScreen renders graph with nodes and edges; panel opens on click
```

---

## Phase F7 — `DraftsScreen`

**Goal:** Split-pane view — artifact list on the left, inline Markdown editor on the right. Auto-save on blur and Ctrl+S.

**Depends on:** F2 (`useNodes`, `useCreateNode`, `useUpdateNode`), F3 (routing with `:nodeId` param).

### Files to Create

#### `frontend/src/components/drafts/DraftList.tsx`

Props:
```typescript
interface DraftListProps {
  nodeId: string | null;
  onSelect: (node: ArtifactNode) => void;
}
```

- Calls `useNodeList("Artifact")` but then filters client-side to nodes linked to the active project (using the project node id set from `useProjectGraph`).
- Lists draft titles; selected item highlighted.
- "+ New Draft" button opens `<NewDraftModal />`.
- Loading skeleton: 3 ghost rows.
- Empty state: "No drafts yet. Create one above."

#### `frontend/src/components/drafts/NewDraftModal.tsx`

- Text input "Draft title".
- On submit: `useCreateNode()` with `{ node_type: "Artifact", title }` then `linkNodeToProject(activeProjectId, newNode.id, "HAS_ARTIFACT")`.
- On success: calls `onCreated(node)` prop which selects the new draft and closes the modal.

#### `frontend/src/components/drafts/DraftEditor.tsx`

Props:
```typescript
interface DraftEditorProps {
  node: ArtifactNode;
  onSave: (content: string) => void;
}
```

Responsibilities:
1. On mount / node change: load content from `content_path`. Because `content_path` is a server-side filesystem path (not a URL), the backend does not currently serve draft file content over HTTP. **Solution:** Use `node.metadata.content_body` as the in-memory content field. Store content in `metadata.content_body` on save via `PUT /nodes/{id}` with updated `metadata`. This mirrors the strategy in the implementation plan's "Decision: Use `content_path`" note but adapts it for the web client which cannot access the filesystem directly.
2. CodeMirror editor instance initialised with `@codemirror/lang-markdown` and a minimal dark theme (or system-preference via `matchMedia`).
3. Auto-save on blur: calls `onSave(content)`.
4. Ctrl+S handler via a CodeMirror keymap extension: calls `onSave(content)`.
5. "Saved ✓" / "Saving..." / "Save failed" status indicator in the top-right corner of the editor pane.

#### `frontend/src/screens/DraftsScreen.tsx`

State:
- `selectedNode: ArtifactNode | null`

Layout:
```
┌────────────────┬──────────────────────────────┐
│ <DraftList />  │  <DraftEditor />  (or empty) │
│ w-72           │  flex-1                      │
└────────────────┴──────────────────────────────┘
```

- Reads `:nodeId` from URL params (`useParams`). If present, selects that node on mount.
- On `onSave(content)`: calls `useUpdateNode()` mutation with `{ metadata: { ...node.metadata, content_body: content } }`. Invalidates `['node', nodeId]`.
- "No draft selected" placeholder in editor pane when nothing selected.

### Tests to Write

File: `frontend/src/screens/__tests__/DraftsScreen.test.tsx`

| Test | Assertion |
|---|---|
| `renders split layout` | Both panels present |
| `selects draft from URL param` | `:nodeId` param auto-selects node |
| `new draft modal creates and selects` | POST fires; new node selected in editor |
| `auto-save on blur calls PUT` | `PUT /nodes/{id}` fired with content |
| `Ctrl+S triggers save` | Same assertion via keyboard event simulation |
| `save status cycles correctly` | "Saving..." → "Saved ✓" after mutation resolves |

File: `frontend/src/components/drafts/__tests__/DraftEditor.test.tsx`

| Test | Assertion |
|---|---|
| `loads initial content from metadata` | Editor populated with `metadata.content_body` |
| `empty content for new node` | Empty editor when `metadata.content_body` absent |

### Validation

```bash
npm run test src/screens/__tests__/DraftsScreen.test.tsx src/components/drafts
# Manual: create draft, type text, blur → fire GET /nodes/{id} to confirm metadata updated
```

---

## Phase F8 — `AgentScreen`

**Goal:** Goal input + live SSE progress feed + rendered final report.

**Depends on:** F1 (`streamResearch` in `api/agent.ts`), F3 (routing).

### Files to Create

#### `frontend/src/components/agent/GoalForm.tsx`

Props:
```typescript
interface GoalFormProps {
  onSubmit: (goal: string, depth: ResearchDepth) => void;
  isRunning: boolean;
}
```

- Multi-line `<textarea>` for goal (3 rows).
- Depth radio group: quick | standard | deep.
- "Run Research" button — disabled when `isRunning` or goal is empty.
- While running: button label changes to "Running…" with a spinner icon; pressing it again is a no-op (the hook manages cancellation internally).

#### `frontend/src/components/agent/ProgressFeed.tsx`

Props:
```typescript
interface ProgressFeedProps {
  events: SseNodeEvent[];
  isRunning: boolean;
}
```

- Renders an ordered list of agent node names.
- Each row: status icon (⏳ pending, ✅ done, ❌ error), node name, status text.
- Nodes seen in events are marked done; the last node is ⏳ if `isRunning`.
- Known nodes in order: `["planner", "searcher", "scraper", "synthesiser"]` — unlisted nodes still render in order received.

#### `frontend/src/components/agent/ReportPanel.tsx`

Props:
```typescript
interface ReportPanelProps {
  report: string | null;
  artifactId: string | null;
}
```

- Renders `<ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>` when `report` is non-null.
- "View in Map →" `<Link>` that navigates to `/map` (visible when `artifactId` is non-null).
- "Copy Report" button using `navigator.clipboard.writeText`.
- `null` state: invisible (parent conditionally renders).

#### `frontend/src/screens/AgentScreen.tsx`

State:
```typescript
const [events, setEvents] = useState<SseNodeEvent[]>([]);
const [report, setReport] = useState<string | null>(null);
const [artifactId, setArtifactId] = useState<string | null>(null);
const [isRunning, setIsRunning] = useState(false);
const [error, setError] = useState<string | null>(null);
const abortRef = useRef<(() => void) | null>(null);
```

On form submit:
1. Clear previous state (`events = [], report = null, error = null`).
2. Set `isRunning = true`.
3. Call `streamResearch(goal, depth, onEvent, onDone, onError)`, store abort fn in `abortRef`.
4. `onEvent`: if `event.event === "node"`, append to `events`.
5. `onDone`: set `isRunning = false`.
6. `onError`: set `error = event.detail`, `isRunning = false`.
7. On `SseDoneEvent`: set `report`, `artifactId`, then call `linkNodeToProject(activeProjectId, artifactId, "HAS_ARTIFACT")` via the `linkNodeToProject` API function (fire-and-forget).

`useEffect` cleanup: call `abortRef.current?.()` on unmount.

Layout:
```
<GoalForm onSubmit={...} isRunning={isRunning} />
{error && <ErrorBanner message={error} />}
{events.length > 0 && <ProgressFeed events={events} isRunning={isRunning} />}
{report && <ReportPanel report={report} artifactId={artifactId} />}
```

### Tests to Write

File: `frontend/src/screens/__tests__/AgentScreen.test.tsx`

| Test | Assertion |
|---|---|
| `renders goal form` | Textarea and Run button visible |
| `run button disabled when empty goal` | Disabled attribute present |
| `progress events render in order` | After SSE node events, 4 rows visible |
| `report renders as markdown` | `<h2>` heading found in DOM after done event |
| `view in map link present after done` | `<a href="/map">` visible |
| `error banner shown on SSE error` | Error detail text visible |
| `abort called on unmount` | Abort ref called when component unmounts |
| `links artifact to project on done` | `POST /projects/{id}/link` called |

File: `frontend/src/api/__tests__/agent.test.ts`

| Test | Assertion |
|---|---|
| `onEvent called for each data line` | 3 data lines → 3 onEvent calls |
| `onDone called after done event` | `onDone` called once |
| `abort stops stream` | After abort, no further callbacks |

### Validation

```bash
npm run test src/screens/__tests__/AgentScreen.test.tsx src/api/__tests__/agent.test.ts
# Manual: run research, observe live progress, read report
```

---

## Phase F9 — Integration, Polish & Hardening

**Goal:** End-to-end coherence, error boundaries, loading states, and cross-screen data freshness.

**Depends on:** F4–F8 all complete.

### Files to Create / Modify

#### `frontend/src/components/layout/ErrorBoundary.tsx`

React class component implementing `componentDidCatch`. Wraps each screen in `AppShell`. Shows "Something went wrong" with a Reload button on any unhandled render error.

#### `frontend/src/components/ui/Spinner.tsx`

Reusable spinner component (Tailwind animated pulse). Used in all loading states.

#### `frontend/src/components/ui/Badge.tsx`

Coloured pill badge. Props: `label: string`, `variant: "source" | "artifact" | "chunk" | "project"`. Used in `NodeResultCard` and `NodeDetailPanel`.

#### `frontend/src/components/ui/EmptyState.tsx`

Centred empty state block. Props: `message: string`, optional `action: ReactNode`.

#### `frontend/src/test-setup.ts`

```typescript
import '@testing-library/jest-dom';
```

#### `frontend/src/test-utils.tsx`

```typescript
// renderWithProviders — wraps tree in QueryClientProvider + MemoryRouter + Zustand reset
```

Helper used by all screen tests to ensure clean state between test cases.

#### MSW Setup (`frontend/src/mocks/`)

| File | Purpose |
|---|---|
| `handlers.ts` | Default MSW handlers matching all backend routes |
| `server.ts` | MSW Node server for Vitest |
| `browser.ts` | MSW Service Worker for browser dev (optional, for manual testing) |

Default handlers must cover: `GET /projects`, `POST /projects`, `GET /projects/:id`, `GET /projects/:id/nodes`, `GET /projects/:id/graph`, `POST /projects/:id/link`, `GET /projects/:id/export`, `POST /ingest/url`, `POST /ingest/pdf`, `GET /search`, `GET /nodes`, `POST /nodes`, `GET /nodes/:id`, `PUT /nodes/:id`, `DELETE /nodes/:id`, `POST /research` (streamed SSE mock).

#### `.env.test`

```
VITE_API_BASE_URL=http://localhost:8000
```

### Cross-Cutting Changes to Apply

1. **Query invalidation consistency:** After `POST /ingest/*` + `POST /projects/{id}/link`, invalidate `['projects', activeProjectId, 'graph']` and `['nodes']` in all relevant mutations.
2. **No-project guard:** All screens except `AgentScreen` check `activeProjectId !== null`; if null, render `<EmptyState message="Select a project in the sidebar to get started." />`.
3. **Error boundary:** Wrap `<LibraryScreen />`, `<MapScreen />`, `<DraftsScreen />`, `<AgentScreen />` individually in `<ErrorBoundary>` inside `AppShell`.

### Tests to Write

File: `frontend/src/components/layout/__tests__/ErrorBoundary.test.tsx`

| Test | Assertion |
|---|---|
| `catches render error` | "Something went wrong" visible when child throws |
| `reload button present` | Button with "Reload" label visible |

### Full Test Run

```bash
npm run test
# All tests pass
npm run build
# Zero TypeScript errors; dist/ generated
```

---

## Phase F10 — E2E Smoke Tests (Optional, Playwright)

**Goal:** Validate the full user journey against a live backend in a controlled environment.

**Depends on:** All prior phases complete; backend running on `localhost:8000`.

### Files to Create

| File | Purpose |
|---|---|
| `frontend/e2e/playwright.config.ts` | Playwright config: baseURL + webServer command |
| `frontend/e2e/journey.spec.ts` | Full user journey test |

### Journey Test Scenarios

1. **Project creation:** Open app → "+ New Project" → type name → "Create" → sidebar shows new name.
2. **URL ingest:** Navigate to Library → paste URL → "Add" → result card appears.
3. **Map view:** Navigate to Map → nodes and edges rendered → click node → panel opens.
4. **Draft creation:** Navigate to Drafts → "+ New Draft" → type title → editor opens → type content → blur → save indicator shows "Saved".
5. **Agent research:** Navigate to Agent → type goal → "Run Research" → progress rows appear → report rendered.

### Validation

```bash
npx playwright install chromium
npm run e2e
```

---

## Dependency Graph

```
F0 (Scaffold)
  └─ F1 (Types + API Client)
        └─ F2 (State Management)
              ├─ F3 (App Shell + Routing)
              │     └─ F4 (ProjectSwitcher)
              │           ├─ F5 (LibraryScreen)
              │           ├─ F6 (MapScreen)
              │           ├─ F7 (DraftsScreen)
              │           └─ F8 (AgentScreen)
              │                 └─ F9 (Polish + Hardening)
              │                       └─ F10 (E2E — optional)
              └─ F8 also needs F1 directly (streamResearch)
```

Phases F5, F6, F7, F8 are **independent of each other** once F2, F3, F4 are done and can be implemented in any order or in parallel.

---

## File Inventory

### New Files (all in `frontend/`)

| File | Phase | Purpose |
|---|---|---|
| `package.json` | F0 | NPM manifest |
| `vite.config.ts` | F0 | Vite + Vitest config |
| `tsconfig.json` | F0 | Browser TS config |
| `tsconfig.node.json` | F0 | Node (Vite config) TS config |
| `tailwind.config.ts` | F0 | Tailwind content paths |
| `postcss.config.js` | F0 | PostCSS plugins |
| `index.html` | F0 | HTML entry point |
| `.env.development` | F0 | API base URL env var |
| `src/main.tsx` | F0 | React root mount |
| `src/App.tsx` | F0→F2 | Providers + router |
| `src/test-setup.ts` | F9 | jest-dom import |
| `src/test-utils.tsx` | F9 | `renderWithProviders` helper |
| `src/types/index.ts` | F1 | Shared TS interfaces |
| `src/api/client.ts` | F1 | Axios instance |
| `src/api/projects.ts` | F1 | Project API calls |
| `src/api/library.ts` | F1 | Ingest + search calls |
| `src/api/nodes.ts` | F1 | Node CRUD calls |
| `src/api/agent.ts` | F1 | SSE stream helper |
| `src/stores/projectStore.ts` | F2 | Zustand active project store |
| `src/hooks/useProjects.ts` | F2 | TanStack Query project hooks |
| `src/hooks/useProjectGraph.ts` | F2 | Graph query hook |
| `src/hooks/useNodes.ts` | F2 | Node query/mutation hooks |
| `src/hooks/useSearch.ts` | F2 | Search query hook |
| `src/components/layout/AppShell.tsx` | F3 | Two-column layout |
| `src/components/layout/NavBar.tsx` | F3 | Vertical nav links |
| `src/components/layout/ErrorBoundary.tsx` | F9 | React error boundary |
| `src/components/sidebar/ProjectSwitcher.tsx` | F4 | Active project + switcher |
| `src/components/sidebar/NewProjectModal.tsx` | F4 | Create project form |
| `src/components/library/AddSourcePanel.tsx` | F5 | URL/PDF ingest |
| `src/components/library/SearchBar.tsx` | F5 | Search input + mode |
| `src/components/library/NodeResultCard.tsx` | F5 | Search result row |
| `src/screens/LibraryScreen.tsx` | F5 | Library screen |
| `src/components/map/customNodes/ProjectNode.tsx` | F6 | React Flow project node |
| `src/components/map/customNodes/SourceNode.tsx` | F6 | React Flow source node |
| `src/components/map/customNodes/ArtifactNode.tsx` | F6 | React Flow artifact node |
| `src/components/map/GraphCanvas.tsx` | F6 | React Flow canvas |
| `src/components/map/NodeDetailPanel.tsx` | F6 | Selected node panel |
| `src/screens/MapScreen.tsx` | F6 | Map screen |
| `src/components/drafts/DraftList.tsx` | F7 | Artifact list panel |
| `src/components/drafts/NewDraftModal.tsx` | F7 | Create draft form |
| `src/components/drafts/DraftEditor.tsx` | F7 | CodeMirror editor |
| `src/screens/DraftsScreen.tsx` | F7 | Drafts screen |
| `src/components/agent/GoalForm.tsx` | F8 | Research goal form |
| `src/components/agent/ProgressFeed.tsx` | F8 | SSE event list |
| `src/components/agent/ReportPanel.tsx` | F8 | Final report renderer |
| `src/screens/AgentScreen.tsx` | F8 | Agent screen |
| `src/components/ui/Spinner.tsx` | F9 | Loading spinner |
| `src/components/ui/Badge.tsx` | F9 | Node type badge |
| `src/components/ui/EmptyState.tsx` | F9 | Empty state block |
| `src/mocks/handlers.ts` | F9 | MSW default handlers |
| `src/mocks/server.ts` | F9 | MSW Node server |
| `e2e/playwright.config.ts` | F10 | Playwright config |
| `e2e/journey.spec.ts` | F10 | Full journey E2E test |

### Files to Modify (Backend — minimal changes)

| File | Change | Phase |
|---|---|---|
| `backend/api/routers/nodes.py` | Verify `GET /nodes?type=Artifact` filter works; add if missing | F7 |

> The nodes router must support `?type=Artifact` query param to filter the list. Inspect `backend/api/routers/nodes.py` and confirm `node_type` filtering is implemented. If not, add a `type: str | None = None` query param that passes through to the DB layer.

---

## Key Design Decisions

| Decision | Rationale | Risk |
|---|---|---|
| `frontend/` as a sibling to `backend/` | Clean separation; no Python configuration touches JS | Requires separate `npm run dev` process alongside `uvicorn` |
| Fetch API for SSE (not `EventSource`) | `/research` is POST; `EventSource` only supports GET | More verbose parsing code; thoroughly tested in unit tests |
| Store draft content in `metadata.content_body` | Browser cannot access server filesystem paths | Content stored in SQLite rows, not files — diverges slightly from CLI design |
| Client-side search scoping | `/search` has no project filter param; avoids backend change | Client filters after fetch — slightly wasteful; mark with TODO |
| dagre auto-layout for graph | No manual positioning needed; suits exploratory data | Large graphs may layout slowly; add a `useMemo` around conversion |
| CodeMirror 6 for editor | Extensible, performant, no React version conflicts | More setup boilerplate than a simple `<textarea>` |
| MSW for test mocking | Tests run without a real backend; same handlers in dev and CI | SSE stream mocking requires a custom MSW handler using `ReadableStream` |
