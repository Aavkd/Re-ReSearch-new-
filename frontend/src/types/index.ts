/**
 * Shared TypeScript interfaces mirroring the backend's serialisation helpers.
 *
 * All timestamps (`created_at`, `updated_at`) are Unix epoch integers as
 * returned by the SQLite layer.
 */

// ---------------------------------------------------------------------------
// Node types
// ---------------------------------------------------------------------------

export interface BaseNode {
  id: string;
  node_type: string;
  title: string;
  content_path: string | null;
  metadata: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}

export interface ProjectNode extends BaseNode {
  node_type: "Project";
}

export interface SourceNode extends BaseNode {
  node_type: "Source";
}

export interface ArtifactNode extends BaseNode {
  node_type: "Artifact";
}

/** Union of the three primary application node types. */
export type AppNode = ProjectNode | SourceNode | ArtifactNode;

// ---------------------------------------------------------------------------
// Edge / graph
// ---------------------------------------------------------------------------

export interface Edge {
  source_id: string;
  target_id: string;
  relation_type: string;
  created_at: number;
}

export interface ProjectGraph {
  nodes: AppNode[];
  edges: Edge[];
}

// ---------------------------------------------------------------------------
// Project summary
//
// NOTE: The implementation plan describes `recent_artifacts: ArtifactNode[]`
// but the current backend (`db/projects.py::get_project_summary`) appends
// `n.title` (strings) rather than full node objects.  The type below matches
// the actual API response.  Update this to `ArtifactNode[]` if the backend is
// changed in a future iteration.
// ---------------------------------------------------------------------------

export interface ProjectSummary {
  project_id: string;
  by_type: Record<string, number>;
  recent_artifacts: string[];
}

// ---------------------------------------------------------------------------
// Ingest
// ---------------------------------------------------------------------------

export interface IngestResponse {
  node_id: string;
  title: string;
  node_type: string;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Search / agent
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  ts: number; // Unix timestamp
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: number;
  updated_at: number;
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
