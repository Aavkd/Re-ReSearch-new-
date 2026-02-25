import { apiClient } from "./client";
import type { AppNode } from "../types";

/** List all nodes, optionally filtered by node_type. */
export async function fetchNodes(type?: string): Promise<AppNode[]> {
  const params = type ? { type } : {};
  const res = await apiClient.get<AppNode[]>("/nodes", { params });
  return res.data;
}

/** Fetch a single node by id. */
export async function fetchNode(id: string): Promise<AppNode> {
  const res = await apiClient.get<AppNode>(`/nodes/${id}`);
  return res.data;
}

/** Create a new graph node. */
export async function createNode(payload: Partial<AppNode>): Promise<AppNode> {
  const res = await apiClient.post<AppNode>("/nodes", payload);
  return res.data;
}

/** Update fields on an existing node. */
export async function updateNode(
  id: string,
  payload: Partial<AppNode>
): Promise<AppNode> {
  const res = await apiClient.put<AppNode>(`/nodes/${id}`, payload);
  return res.data;
}

/** Delete a node (edges cascade). */
export async function deleteNode(id: string): Promise<void> {
  await apiClient.delete(`/nodes/${id}`);
}
