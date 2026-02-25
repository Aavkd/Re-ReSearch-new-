import { apiClient } from "./client";
import type { AppNode, ProjectSummary, ProjectGraph } from "../types";

/** Return all Project nodes. */
export async function fetchProjects(): Promise<AppNode[]> {
  const res = await apiClient.get<AppNode[]>("/projects");
  return res.data;
}

/** Create a new Project node and return it. */
export async function createProject(name: string): Promise<AppNode> {
  const res = await apiClient.post<AppNode>("/projects", { name });
  return res.data;
}

/** Return summary stats for a project: node counts by type, recent artifacts. */
export async function fetchProjectSummary(id: string): Promise<ProjectSummary> {
  const res = await apiClient.get<ProjectSummary>(`/projects/${id}`);
  return res.data;
}

/**
 * Return all nodes reachable from the project within `depth` hops.
 * Defaults to depth=2 (matches backend default).
 */
export async function fetchProjectNodes(
  id: string,
  depth?: number
): Promise<AppNode[]> {
  const params = depth !== undefined ? { depth } : {};
  const res = await apiClient.get<AppNode[]>(`/projects/${id}/nodes`, {
    params,
  });
  return res.data;
}

/** Return the project subgraph (nodes + edges) for graph-canvas rendering. */
export async function fetchProjectGraph(id: string): Promise<ProjectGraph> {
  const res = await apiClient.get<ProjectGraph>(`/projects/${id}/graph`);
  return res.data;
}

/** Link an existing node to this project with the given relation. */
export async function linkNodeToProject(
  projectId: string,
  nodeId: string,
  relation = "HAS_SOURCE"
): Promise<void> {
  await apiClient.post(`/projects/${projectId}/link`, {
    node_id: nodeId,
    relation,
  });
}

/** Serialise the full project subgraph to JSON (export). */
export async function exportProject(id: string): Promise<unknown> {
  const res = await apiClient.get<unknown>(`/projects/${id}/export`);
  return res.data;
}
