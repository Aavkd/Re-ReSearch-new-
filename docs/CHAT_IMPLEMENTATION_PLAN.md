# Re:Search — Knowledge-Base Chat Feature: Implementation Plan

## Overview

Add a **project-scoped conversational chat** that grounds every answer in the
active project's knowledge base using the existing RAG pipeline (`backend/rag/recall.py`
+ `hybrid_search`). Users send multi-turn messages; the backend retrieves
relevant chunks, streams a token-by-token response via SSE, and cites the
source nodes used.

The feature is split into **two tracks** (backend and frontend) across **eight
discrete phases**. Each phase lists the exact files to create or modify,
the purpose of every change, and validation steps.

---

## Architecture Summary

```
Browser  ──POST /projects/{id}/chat/{cid}/messages──▶  FastAPI (SSE stream)
                                                              │
                                          ┌───────────────────┤
                                          │  backend/rag/chat  │  ← new service
                                          └──────┬────────────┘
                                                 │
                                   hybrid_search (existing)
                                                 │
                                           SQLite / FTS5 / vec
```

**Data model:** Conversations are `Chat` nodes in the existing `nodes` table
(no new table needed). Messages are stored as a JSON array in `metadata.messages`.
A directed edge (`CONVERSATION_IN`) links each Chat node to its Project node.

---

## Dependencies Between Phases

```
B-C1 → B-C2 → B-C3 → B-C5   (backend track — must run in order)
              B-C3 → B-C4    (chat service needed before router is complete)
B-C5 ─────────────────────▶  F-C1 → F-C2 → F-C3 → F-C4 → F-C5 → F-C6 → F-C7 → F-C8
```

Backend phases must be completed before frontend integration work starts
(F-C2 onward). F-C1 (TypeScript types) can begin in parallel with backend work.

---

## Phase B-C1 — Database Layer for Chat Nodes

**Goal:** Provide CRUD helpers for `Chat` nodes and their message payloads
without altering the schema (the `Chat` node type already exists in the docs
and the schema supports arbitrary `node_type` strings).

### Files to Create

#### `backend/db/chat.py`

| Function | Signature | Purpose |
|---|---|---|
| `create_conversation` | `(conn, project_id, title) → Node` | Insert a `Chat` node; create a `CONVERSATION_IN` edge to the project; return the node. |
| `get_conversation` | `(conn, conv_id) → Node \| None` | Fetch the Chat node by UUID. |
| `list_conversations` | `(conn, project_id) → list[Node]` | Return all Chat nodes linked to the project via `CONVERSATION_IN` edges, ordered by `updated_at DESC`. |
| `append_messages` | `(conn, conv_id, messages: list[dict]) → Node` | Merge new messages into `metadata.messages` and update `updated_at`. |
| `delete_conversation` | `(conn, conv_id) → None` | Delete the Chat node (CASCADE removes its edges). |

**Message dict shape** (stored in `metadata.messages`):
```json
{ "role": "user" | "assistant", "content": "...", "ts": 1700000000 }
```

### Files to Modify

| File | Change |
|---|---|
| `backend/db/__init__.py` | Export `chat` sub-module so callers can `from backend.db import chat`. |

### Validation

- Unit test `tests/test_chat_db.py`:
  - `test_create_conversation_creates_node_and_edge`
  - `test_list_conversations_scoped_to_project`
  - `test_append_messages_updates_metadata`
  - `test_delete_conversation_cascades`

---

## Phase B-C2 — RAG Chat Service

**Goal:** Implement multi-turn, citation-aware answer generation as an async
generator so the router can stream tokens over SSE.

### Files to Create

#### `backend/rag/chat.py`

```python
async def chat_stream(
    conn: sqlite3.Connection,
    question: str,
    history: list[dict],   # prior {"role", "content"} turns
    project_id: str | None = None,
    top_k: int = 5,
) -> AsyncIterator[str]:
    """
    Yields SSE-formatted strings:
      data: {"event": "token",   "text": "..."}
      data: {"event": "citation","nodes": [{id, title, url}]}
      data: {"event": "done"}
      data: {"event": "error",   "detail": "..."}
    """
```

**Implementation steps inside `chat_stream`:**

1. Resolve project scope IDs (reuse `get_project_nodes` exactly as `recall.py` does).
2. Embed the latest `question` with `embed_text`.
3. Call `hybrid_search` with `scope_ids` to fetch `top_k` chunks.
4. Build a system prompt that includes:
   - Numbered source chunks (same format as `recall.py`).
   - Conversation history summary (last N turns, truncated to stay within context window).
5. Call the LLM with **streaming enabled** (`stream=True` on ChatOllama / ChatOpenAI).
6. `yield` each `token` chunk as `{"event": "token", "text": chunk}`.
7. After the stream completes, `yield` a `citation` event listing the node IDs and titles used.
8. `yield` a final `{"event": "done"}`.
9. Wrap in `try/except`; on error, `yield` `{"event": "error", "detail": str(exc)}`.

**LLM streaming notes:**
- `ChatOllama` supports `astream()` — use `async for chunk in llm.astream(messages)`.
- `ChatOpenAI` also supports `astream()`.
- Build the `messages` list using LangChain `SystemMessage` + `HumanMessage` / `AIMessage` from `history`.

### Files to Modify

| File | Change |
|---|---|
| `backend/rag/__init__.py` | Export `chat_stream` for import convenience. |

### Validation

- Unit test `tests/test_chat_rag.py`:
  - `test_chat_stream_yields_token_then_citation_then_done` (mock LLM + DB)
  - `test_chat_stream_no_results_yields_fallback`
  - `test_chat_stream_scoped_to_project`

---

## Phase B-C3 — Chat API Router

**Goal:** Expose the chat feature as REST + SSE endpoints under
`/projects/{project_id}/chat`.

### Files to Create

#### `backend/api/routers/chat.py`

| Method | Path | Body / Params | Response | Purpose |
|---|---|---|---|---|
| `GET` | `/projects/{project_id}/chat` | — | `list[ChatConversationOut]` | List all conversations for the project. |
| `POST` | `/projects/{project_id}/chat` | `{"title": "..."}` | `ChatConversationOut` | Create a new (empty) conversation. |
| `GET` | `/projects/{project_id}/chat/{conv_id}` | — | `ChatConversationOut` | Fetch a conversation with its full message history. |
| `POST` | `/projects/{project_id}/chat/{conv_id}/messages` | `{"message": "...", "history": [...]}` | SSE stream | Send a message; stream token events back. |
| `DELETE` | `/projects/{project_id}/chat/{conv_id}` | — | `204 No Content` | Delete a conversation. |

**Pydantic schemas:**

```python
class NewConversationRequest(BaseModel):
    title: str = "New conversation"

class ChatMessageRequest(BaseModel):
    message: str
    history: list[dict] = []   # client-managed history for context

class ChatConversationOut(BaseModel):
    id: str
    title: str
    messages: list[dict]
    created_at: int
    updated_at: int
```

**SSE streaming endpoint logic (`POST .../messages`):**

1. Persist the user message immediately via `append_messages`.
2. Start `chat_stream(...)` (async generator).
3. Collect all streamed tokens into a buffer while also yielding them.
4. After `"done"`, persist the full assistant reply via `append_messages`.
5. Return a `StreamingResponse` with `media_type="text/event-stream"`.

Each SSE frame:
```
data: {"event": "token",    "text": " ..."}
data: {"event": "citation", "nodes": [{"id":"...", "title":"...", "url":"..."}]}
data: {"event": "done"}
```

**Error handling:** 404 if `project_id` or `conv_id` not found; 503 if embedding
service unavailable (propagated from `chat_stream`).

### Validation

- Integration test `tests/test_api_chat.py`:
  - `test_create_and_list_conversation`
  - `test_get_conversation_returns_messages`
  - `test_post_message_streams_sse`  (collect full response, assert token + done events)
  - `test_delete_conversation_returns_204`
  - `test_post_message_404_unknown_project`

---

## Phase B-C4 — Register Chat Router in `app.py`

**Goal:** Mount the new router so it is reachable by the frontend.

### Files to Modify

#### `backend/api/app.py`

- Import `chat as chat_router` from `backend.api.routers`.
- Add `app.include_router(chat_router.router, prefix="/projects", tags=["chat"])`.
- Update `version` to `"0.3.0"`.

**Note:** The prefix is `/projects` (not `/projects/{id}/chat`) so the router's
own path definitions (`/projects/{project_id}/chat/...`) align naturally with
the existing `/projects` family.

#### `README.md`

Add the new endpoints to the **Endpoints** table:

| Method | Path | Description |
|---|---|---|
| `GET` | `/projects/{id}/chat` | List conversations |
| `POST` | `/projects/{id}/chat` | Create conversation |
| `GET` | `/projects/{id}/chat/{cid}` | Get conversation + messages |
| `POST` | `/projects/{id}/chat/{cid}/messages` | Send message (SSE stream) |
| `DELETE` | `/projects/{id}/chat/{cid}` | Delete conversation |

### Validation

```bash
uvicorn backend.api.app:app --reload
# curl http://localhost:8000/docs  →  chat endpoints visible in Swagger UI
pytest tests/test_api_chat.py -v
```

---

## Phase F-C1 — TypeScript Types

**Goal:** Define all shared chat-related interfaces so every subsequent
frontend phase can import without re-defining shapes.

**Depends on:** F0 scaffold (already complete).  Can run in parallel with backend.

### Files to Modify

#### `frontend/src/types/index.ts`

Add the following interfaces:

```typescript
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  ts: number;             // Unix timestamp
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatTokenEvent {
  event: "token";
  text: string;
}

export interface ChatCitationEvent {
  event: "citation";
  nodes: Array<{ id: string; title: string; url?: string }>;
}

export interface ChatDoneEvent {
  event: "done";
}

export interface ChatErrorEvent {
  event: "error";
  detail: string;
}

export type ChatSseEvent =
  | ChatTokenEvent
  | ChatCitationEvent
  | ChatDoneEvent
  | ChatErrorEvent;
```

### Validation

```bash
cd frontend && npm run build   # zero TypeScript errors
```

---

## Phase F-C2 — API Client for Chat

**Goal:** Thin wrapper around the backend chat endpoints.

### Files to Create

#### `frontend/src/api/chat.ts`

| Function | Signature | Backend call |
|---|---|---|
| `listConversations` | `(projectId: string) → Promise<ChatConversation[]>` | `GET /projects/{id}/chat` |
| `createConversation` | `(projectId: string, title?: string) → Promise<ChatConversation>` | `POST /projects/{id}/chat` |
| `getConversation` | `(projectId: string, convId: string) → Promise<ChatConversation>` | `GET /projects/{id}/chat/{cid}` |
| `deleteConversation` | `(projectId: string, convId: string) → Promise<void>` | `DELETE /projects/{id}/chat/{cid}` |
| `streamChatMessage` | `(projectId, convId, message, history, onEvent, onDone, onError) → () => void` | `POST /projects/{id}/chat/{cid}/messages` (SSE via `fetch` + `ReadableStream`) |

**`streamChatMessage` implementation notes:**
- Use `fetch` + `AbortController` + `ReadableStream` exactly as `api/agent.ts` does
  (POST endpoint — `EventSource` cannot be used).
- Parse SSE frames: split on `\n\n`, extract `data:` JSON, dispatch to `onEvent`.
- On `"done"` event, call `onDone()`.
- On `"error"` event or network failure, call `onError(new Error(...))`.
- Return the `abort` function for `useEffect` cleanup.

### Files to Create (tests)

#### `frontend/src/api/__tests__/chat.test.ts`

| Test | Assertion |
|---|---|
| `listConversations returns array` | Parses response body into `ChatConversation[]` |
| `createConversation posts correct body` | Body is `{ title: "..." }` |
| `streamChatMessage dispatches token events` | `onEvent` called with token payloads |
| `streamChatMessage calls onDone on done event` | `onDone` invoked once after stream |
| `abort stops dispatching events` | After `abort()`, no further `onEvent` calls |

### Validation

```bash
npm run test src/api/__tests__/chat.test.ts
```

---

## Phase F-C3 — Chat Zustand Store

**Goal:** Manage the active conversation and in-memory optimistic message state.

### Files to Create

#### `frontend/src/stores/chatStore.ts`

```typescript
interface ChatStore {
  // Active conversation selection
  activeConvId: string | null;
  setActiveConv: (id: string | null) => void;

  // Optimistic in-memory messages for the active conversation
  // (supplements persisted messages from server)
  localMessages: ChatMessage[];
  addLocalMessage: (msg: ChatMessage) => void;
  clearLocalMessages: () => void;

  // Streaming state
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;

  // In-progress assistant reply (assembled token by token)
  streamingContent: string;
  appendStreamingContent: (text: string) => void;
  resetStreamingContent: () => void;

  // Citations from the last assistant reply
  citations: Array<{ id: string; title: string; url?: string }>;
  setCitations: (c: typeof this.citations) => void;
}
```

- **No persistence** — conversation list is always fetched from the server; only
  `activeConvId` may optionally be persisted to `sessionStorage` (not
  `localStorage`) so it resets on new browser sessions.

### Files to Create (tests)

#### `frontend/src/stores/__tests__/chatStore.test.ts`

| Test | Assertion |
|---|---|
| `initial streaming state is false` | `isStreaming` is `false` |
| `appendStreamingContent accumulates text` | Multiple appends concatenate |
| `resetStreamingContent clears to empty` | Back to `""` |
| `addLocalMessage appends to array` | Array length increases |
| `clearLocalMessages empties array` | Array length is 0 |

### Validation

```bash
npm run test src/stores/__tests__/chatStore.test.ts
```

---

## Phase F-C4 — TanStack Query Hooks for Chat

**Goal:** Wrap the chat API functions in React Query for server-state management.

### Files to Modify

#### `frontend/src/hooks/useProjects.ts`

Add the following hooks (keeping them co-located with other project-scoped hooks):

```typescript
// List conversations for the active project
export function useConversationList(projectId: string | null)

// Create a new conversation
export function useCreateConversation()
  // On success: invalidate ['conversations', projectId]

// Delete a conversation
export function useDeleteConversation()
  // On success: invalidate ['conversations', projectId]
  // If deleted conv was active, call chatStore.setActiveConv(null)
```

Alternatively, these can live in a new dedicated `frontend/src/hooks/useChat.ts`
if the file grows large — the implementor should judge by line count.

**Query key convention:**
- `['conversations', projectId]` — list
- `['conversation', projectId, convId]` — single

### Validation

```bash
npm run test src/hooks
```

---

## Phase F-C5 — Chat UI Components

**Goal:** Build the reusable components that `ChatScreen` assembles.

### Files to Create

#### `frontend/src/components/chat/MessageBubble.tsx`

Props:
```typescript
interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean; // true only for the in-progress assistant bubble
}
```

- **User bubble:** right-aligned, blue background, plain text.
- **Assistant bubble:** left-aligned, grey background, content rendered with
  `<ReactMarkdown>` + `remark-gfm` (reuse the dep already in `package.json`).
- **Streaming bubble:** shows `streamingContent` from the store, with a blinking
  cursor appended while `isStreaming` is true.
- Timestamp displayed in `HH:mm` format below the bubble.

#### `frontend/src/components/chat/CitationList.tsx`

Props:
```typescript
interface CitationListProps {
  citations: Array<{ id: string; title: string; url?: string }>;
}
```

- Renders a collapsible "Sources" section below the last assistant bubble.
- Each citation is a `<button>` that navigates to `/library` and highlights the
  node (pass `nodeId` via router `state`), or opens `url` in a new tab if
  present.
- Hidden entirely when `citations` is empty.

#### `frontend/src/components/chat/ConversationList.tsx`

Props:
```typescript
interface ConversationListProps {
  projectId: string;
}
```

- Lists conversations from `useConversationList(projectId)`.
- Active conversation highlighted.
- Clicking a conversation calls `chatStore.setActiveConv(id)` and triggers
  `useQueryClient().invalidateQueries(['conversation', ...])` to refresh messages.
- "+ New Chat" button at top calls `useCreateConversation()`, sets active on success.
- Trash icon per row for deletion (with confirmation tooltip).
- Loading skeleton (3 ghost rows) while fetching.
- "No conversations yet" empty state.

#### `frontend/src/components/chat/ChatInput.tsx`

Props:
```typescript
interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}
```

- `<textarea>` that auto-expands up to 5 lines.
- Send button (arrow icon) disabled when empty or when `disabled` is true.
- `Enter` sends (with `Shift+Enter` for new line).
- Clears after send.

### Files to Create (tests)

#### `frontend/src/components/chat/__tests__/MessageBubble.test.tsx`

| Test | Assertion |
|---|---|
| `renders user message right-aligned` | Has user-bubble class |
| `renders assistant markdown` | Markdown bold rendered as `<strong>` |
| `streaming bubble appends cursor` | `▍` character visible when `isStreaming=true` |

#### `frontend/src/components/chat/__tests__/ChatInput.test.tsx`

| Test | Assertion |
|---|---|
| `send button disabled when empty` | Button has `disabled` attribute |
| `Enter key calls onSend` | `onSend` callback invoked with input value |
| `Shift+Enter inserts newline` | `onSend` NOT called |
| `input clears after send` | Value is `""` after submit |

### Validation

```bash
npm run test src/components/chat
```

---

## Phase F-C6 — `ChatScreen`

**Goal:** Top-level screen that assembles the chat feature.

### Files to Create

#### `frontend/src/screens/ChatScreen.tsx`

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  [ConversationList — 240px fixed left]  [Chat panel]   │
│                                          ┌──────────── │
│                                          │ message list │
│                                          │  (scrollable)│
│                                          ├──────────── │
│                                          │[CitationList]│
│                                          ├──────────── │
│                                          │ [ChatInput]  │
│                                          └──────────── │
└────────────────────────────────────────────────────────┘
```

**State management:**
- Reads `activeProjectId` from `useProjectStore`.
- Reads `activeConvId`, `isStreaming`, `localMessages`, `streamingContent`,
  `citations` from `useChatStore`.
- Server messages fetched via `getConversation` on `activeConvId` change.
- Local messages (optimistic) appended immediately on send; reconciled after
  the stream completes.

**Send flow:**
1. `ChatInput.onSend(text)` fires.
2. Append a `{ role: "user", content: text }` local message immediately.
3. Start SSE stream via `streamChatMessage(...)`.
4. Each `token` event calls `appendStreamingContent`.
5. `citation` event calls `setCitations`.
6. `done` event: assemble full assistant message, call `addLocalMessage`, call
   `resetStreamingContent`, `setIsStreaming(false)`, then
   `queryClient.invalidateQueries(['conversation', ...])` to sync with server.
7. Abort ref cleaned up on unmount.

**Guards:**
- If `activeProjectId` is null: render `<EmptyState>` — "Select a project to start chatting."
- If `activeConvId` is null: render `<EmptyState>` — "Select or create a conversation."

**Auto-scroll:** A `useEffect` scrolls the message list to the bottom whenever
`localMessages` or `streamingContent` changes (use a `bottomRef` sentinel div).

### Files to Create (tests)

#### `frontend/src/screens/__tests__/ChatScreen.test.tsx`

Mock `api/chat.ts` with `vi.mock`.

| Test | Assertion |
|---|---|
| `shows empty state when no project selected` | "Select a project" text visible |
| `shows empty state when no conv selected` | "Select or create" text visible |
| `message list renders user and assistant bubbles` | Both bubble types in DOM |
| `sending a message appends a user bubble optimistically` | User bubble visible before SSE resolves |
| `streaming tokens update streaming bubble` | Partial text appears during stream |
| `done event finalises assistant bubble` | Full text replaces streaming bubble |
| `citations panel appears after done` | Source titles visible |
| `abort called on unmount during streaming` | No further state updates after unmount |

### Validation

```bash
npm run test src/screens/__tests__/ChatScreen.test.tsx
```

---

## Phase F-C7 — Routing & Navigation

**Goal:** Wire the new screen into the React Router tree and add a nav link.

### Files to Modify

#### `frontend/src/App.tsx`

Add the `/chat` route inside the `<Route path="/" element={<AppShell />}>` block:

```tsx
<Route
  path="chat"
  element={
    <ErrorBoundary>
      <ChatScreen />
    </ErrorBoundary>
  }
/>
```

#### `frontend/src/components/layout/NavBar.tsx`

Add a new nav link entry:

| Label | Route |
|---|---|
| Chat | `/chat` |

Insert it between **Agent** and any trailing items (or at the bottom of the
list — follow the existing ordering convention).

### Files to Modify (tests)

#### `frontend/src/components/layout/__tests__/AppShell.test.tsx`

Add one test:

| Test | Assertion |
|---|---|
| `renders Chat nav link` | `<a href="/chat">` or link with text "Chat" present |

### Validation

```bash
npm run build   # zero TypeScript errors
npm run test src/components/layout
# Manual: navigate to http://localhost:5173/chat, verify layout renders
```

---

## Phase F-C8 — Polish & Hardening

**Goal:** Final quality pass — error states, accessibility, keyboard navigation,
and full test coverage.

### Tasks

| Task | File(s) | Notes |
|---|---|---|
| Add `aria-label` to `ChatInput` textarea | `ChatInput.tsx` | Screen reader: "Chat message input" |
| Add `role="log"` + `aria-live="polite"` to message list | `ChatScreen.tsx` | Announces new messages to screen readers |
| `ConversationList` keyboard navigation | `ConversationList.tsx` | Arrow keys move focus between items; Enter selects |
| Error boundary wrapping `ChatScreen` | Already handled in F-C7 via `<ErrorBoundary>` | Verify the existing `ErrorBoundary` component catches render-time errors |
| Loading spinner during conversation switch | `ChatScreen.tsx` | Show `<Spinner />` while `getConversation` is resolving |
| Conversation title editing | `ConversationList.tsx` | Double-click to edit title; `PUT /nodes/{id}` to persist via `useUpdateNode` |
| Throttle streaming token updates | `chatStore.ts` | Batch `appendStreamingContent` calls via `requestAnimationFrame` to avoid excessive re-renders on fast models |
| Add `Chat` to MSW handlers | `frontend/src/mocks/handlers.ts` | Add MSW stubs for all five chat endpoints so tests run offline |

### Validation

```bash
npm run build          # clean build, no TS errors
npm run test           # all tests pass
# Lighthouse accessibility audit on /chat: score ≥ 90
```

---

## Complete File Manifest

### New files

| Path | Phase |
|---|---|
| `backend/db/chat.py` | B-C1 |
| `backend/rag/chat.py` | B-C2 |
| `backend/api/routers/chat.py` | B-C3 |
| `tests/test_chat_db.py` | B-C1 |
| `tests/test_chat_rag.py` | B-C2 |
| `tests/test_api_chat.py` | B-C3 |
| `frontend/src/api/chat.ts` | F-C2 |
| `frontend/src/api/__tests__/chat.test.ts` | F-C2 |
| `frontend/src/stores/chatStore.ts` | F-C3 |
| `frontend/src/stores/__tests__/chatStore.test.ts` | F-C3 |
| `frontend/src/components/chat/MessageBubble.tsx` | F-C5 |
| `frontend/src/components/chat/CitationList.tsx` | F-C5 |
| `frontend/src/components/chat/ConversationList.tsx` | F-C5 |
| `frontend/src/components/chat/ChatInput.tsx` | F-C5 |
| `frontend/src/components/chat/__tests__/MessageBubble.test.tsx` | F-C5 |
| `frontend/src/components/chat/__tests__/ChatInput.test.tsx` | F-C5 |
| `frontend/src/screens/ChatScreen.tsx` | F-C6 |
| `frontend/src/screens/__tests__/ChatScreen.test.tsx` | F-C6 |

### Modified files

| Path | Phase | Change summary |
|---|---|---|
| `backend/db/__init__.py` | B-C1 | Export `chat` submodule |
| `backend/rag/__init__.py` | B-C2 | Export `chat_stream` |
| `backend/api/app.py` | B-C4 | Mount chat router; bump version to 0.3.0 |
| `README.md` | B-C4 | Document new endpoints |
| `frontend/src/types/index.ts` | F-C1 | Add chat-related interfaces |
| `frontend/src/hooks/useProjects.ts` | F-C4 | Add conversation list/create/delete hooks |
| `frontend/src/App.tsx` | F-C7 | Add `/chat` route |
| `frontend/src/components/layout/NavBar.tsx` | F-C7 | Add Chat nav link |
| `frontend/src/components/layout/__tests__/AppShell.test.tsx` | F-C7 | Assert Chat link present |
| `frontend/src/mocks/handlers.ts` | F-C8 | Add MSW stubs for chat endpoints |

---

## Ordered Execution Checklist

```
[x] B-C1  backend/db/chat.py + tests/test_chat_db.py
[x] B-C2  backend/rag/chat.py + tests/test_chat_rag.py
[ ] B-C3  backend/api/routers/chat.py + tests/test_api_chat.py
[ ] B-C4  app.py mount + README update
[ ] F-C1  types/index.ts  (can overlap with B-C1..B-C4)
[ ] F-C2  api/chat.ts + tests
[ ] F-C3  stores/chatStore.ts + tests
[ ] F-C4  hooks (useConversationList, useCreateConversation, useDeleteConversation)
[ ] F-C5  components/chat/* + component tests
[ ] F-C6  screens/ChatScreen.tsx + screen tests
[ ] F-C7  App.tsx route + NavBar link + AppShell test update
[ ] F-C8  Polish: aria, MSW stubs, animation throttle, conversation title edit
```
