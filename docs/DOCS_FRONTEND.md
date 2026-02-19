# Frontend Documentation: Re:Search

## 1. Overview
The frontend of **Re:Search** is a high-performance, local-first web application designed to serve as a "Second Brain." It is built to be hosted within a **Tauri** shell but developed using standard modern web technologies.

The core UX philosophy revolves around a dual-view system:
1.  **Macro View ("Crazy Board"):** A spatial, infinite canvas for organizing thoughts and connections.
2.  **Micro View ("Artifact Editor"):** A focused, distraction-free writing and reading environment.

---

## 2. Core Stack & Setup

### Framework: React + Vite
- **Build Tool:** Vite is selected for its lightning-fast HMR (Hot Module Replacement) and optimized bundling.
- **Framework:** React 18+ (utilizing Functional Components and Hooks).
- **Language:** TypeScript is strictly enforced for type safety across the complex node/edge data structures.

### Styling: Tailwind CSS
- **Utility-First:** Rapid UI development for layout and typography.
- **Theming:** Dark mode support out-of-the-box (essential for knowledge work).
- **Typography:** ` @tailwindcss/typography` plugin is used for rendering clean Markdown content in the editor and preview modes.

### Setup Command
```bash
npm create vite@latest re-search-frontend -- --template react-ts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

## 3. State Management (Zustand)

We use **Zustand** for global state management due to its simplicity, minimal boilerplate, and transient update capabilities (crucial for high-frequency canvas updates).

### Store Structure
The store is divided into slices to manage complexity:

1.  **`CanvasStore`:**
    - Manages `nodes` and `edges` for React Flow.
    - Handles viewport state (zoom, pan).
    - Actions: `addNode`, `connectNodes`, `updateNodePosition`.

2.  **`EditorStore`:**
    - Manages the currently active "Artifact" (document).
    - Tracks dirty state (unsaved changes).
    - Actions: `openArtifact`, `saveContent`, `setMode` (edit/preview).

3.  **`AppStore`:**
    - Manages UI themes, sidebar toggles, and modal states.

### Example Implementation
```typescript
import { create } from 'zustand';
import { Node, Edge } from 'reactflow';

interface CanvasState {
  nodes: Node[];
  edges: Edge[];
  addNode: (node: Node) => void;
  onNodesChange: (changes: any) => void;
}

export const useCanvasStore = create<CanvasState>((set) => ({
  nodes: [],
  edges: [],
  addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),
  onNodesChange: (changes) => {
    // React Flow specific state updates
  }
}));
```

---

## 4. The "Crazy Board" (React Flow)

The **Crazy Board** is the visual heart of the application, implemented using **React Flow**. It allows users to spatialize their knowledge.

### Configuration
- **Background:** Dotted or Grid pattern for spatial reference.
- **Controls:** Standard zoom/pan controls, plus a mini-map for navigation in large graphs.
- **Pro Options:** `fitView` on load to show context.

### Custom Node Types
We extend the default React Flow nodes to create semantic "Cards":

1.  **`DocumentNode`:** Represents a Markdown file. Shows title + snippet. Double-click opens the Editor.
2.  **`SourceNode`:** Represents a web link or PDF. Shows favicon + domain.
3.  **`ImageNode`:** Visual media directly on the canvas.
4.  **`ConceptNode`:** Simple text labels for grouping/labeling clusters (sticky note style).

### Interactions
- **Drag & Drop:** Nodes can be freely moved.
- **Connecting:** Dragging from a handle creates a semantic link (Edge).
- **Selection:** Shift-click or drag-select to group move nodes.
- **Context Menu:** Right-click on canvas to "Add Note" or "Paste Link".

---

## 5. The "Artifact" Editor (Tiptap)

For the writing experience, we use **Tiptap** (headless wrapper around ProseMirror). This provides a "Notion-like" block editing experience while maintaining full control over the UI.

### Configuration
- **Headless:** We build our own toolbar and floating menus.
- **Markdown Support:** Content is serialized to/from Markdown for storage.

### Key Extensions
- **`StarterKit`:** Basic bold, italic, lists, headings.
- **`Markdown`:** Essential for serializing the editor content to clean `.md` files.
- **`Placeholder`:** "Type '/' for commands..." prompt.
- **`Typography`:** Smart quotes, dashes.
- **`CodeBlockLowlight`:** Syntax highlighting for code snippets.

### UX Interactions
- **Slash Commands:** Typing `/` triggers a popup menu to insert headings, lists, or custom components.
- **Floating Menu:** Selecting text reveals a bubble menu for quick formatting (Bold, Link, Highlight).
- **Wiki-Links:** Typing `[[` triggers a search for existing nodes to link to, creating a bi-directional graph connection.

---

## 6. Component Structure

The application structure follows a feature-based organization:

```
src/
├── components/
│   ├── ui/               # Generic UI atoms (Button, Input, Modal)
│   ├── canvas/           # React Flow wrapper & custom nodes
│   │   ├── CrazyBoard.tsx
│   │   ├── nodes/
│   │   │   ├── DocumentNode.tsx
│   │   │   └── SourceNode.tsx
│   │   └── controls/
│   └── editor/           # Tiptap wrapper & extensions
│       ├── ArtifactEditor.tsx
│       ├── Toolbar.tsx
│       └── extensions/
├── stores/               # Zustand stores
│   ├── useCanvasStore.ts
│   └── useEditorStore.ts
├── layouts/
│   └── MainLayout.tsx    # Split pane (Canvas / Editor)
└── hooks/                # Custom hooks (e.g., useKeyboardShortcuts)
```

## 8. Dashboard & Research UI (The "Headquarters")

The application entry point is the **Dashboard**, designed to be the command center for all knowledge operations.

### A. Homepage Layout
- **Hero Section:** Large, inviting input field: *"What do you want to research today?"*
- **Recent Projects:** Grid of cards showing recently accessed project boards (with thumbnail previews of the canvas).
- **Quick Actions:** "New Project", "Open Random Note", "Daily Briefing".

### B. Deep Research Initiation
When the user enters a prompt in the Hero input (e.g., *"State of Solid State Batteries in 2024"*), a **Mission Configuration** modal appears:
1.  **Goal Definition:** Refine the prompt (auto-suggestions by LLM).
2.  **Depth Selector:** "Quick Overview" (5 mins) vs "Deep Dive" (30+ mins, multiple iterations).
3.  **Output Format:** "New Project Board", "Single Summary Document", or "Append to Existing Project".

### C. The "Agent HUD" (Heads-Up Display)
Once a research mission starts, the UI transforms to show the agent's active thought process. This is critical for trust and transparency.

**Visual Components:**
- **Status Ticker:** *Thinking...*, *Searching Google for 'Toyota Battery Patents'*, *Reading PDF...*
- **Live Logs:** A terminal-like scrolling list of actions taken by the LangGraph agent.
- **Resource Stream:** As sources are found (URLs, PDFs), they pop up as cards in a horizontal "Collected" stream.
- **Plan Visualization:** A stepper component showing the agent's current phase:
    1.  [x] **Planning** (Breaking down the query)
    2.  [>] **Exploration** (Iterative searching & reading)
    3.  [ ] **Synthesis** (Compiling findings)
    4.  [ ] **Report Generation** (Creating the final artifact)

### D. Navigation Flow
- **Sidebar:** Always visible (collapsed icon mode).
    - **Home:** Dashboard.
    - **Projects:** List of all knowledge bases.
    - **Search:** Global semantic search across all nodes.
    - **Settings:** LLM keys, local model selection, theme.
- **Breadcrumbs:** `Home > Projects > "Battery Tech" > Canvas`

---

## 9. Component Structure (Updated)

The file structure is expanded to support the Dashboard and Agent UI:

```
src/
├── components/
│   ├── dashboard/        # New Dashboard components
│   │   ├── ProjectCard.tsx
│   │   ├── RecentProjects.tsx
│   │   └── HeroInput.tsx
│   ├── agent/            # Research Agent UI
│   │   ├── AgentHUD.tsx
│   │   ├── LiveLog.tsx
│   │   └── ResourceStream.tsx
│   ├── ... (previous components)
├── routes/               # Routing (React Router)
│   ├── DashboardPage.tsx
│   ├── ProjectView.tsx   # Wraps Canvas + Editor
│   └── SettingsPage.tsx
```