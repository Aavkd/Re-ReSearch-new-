import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { fetchNodes, fetchNode, createNode, updateNode, deleteNode } from "../api/nodes";
import type { AppNode } from "../types";
import { useProjectStore } from "../stores/projectStore";

/** Full list of nodes, optionally filtered by `type`. */
export function useNodeList(type?: string) {
  return useQuery<AppNode[]>({
    queryKey: ["nodes", type],
    queryFn: () => fetchNodes(type),
  });
}

/** Single node by id.  Only fetches when `id` is truthy. */
export function useNode(id: string | null) {
  return useQuery<AppNode>({
    queryKey: ["node", id],
    queryFn: () => fetchNode(id!),
    enabled: !!id,
  });
}

/** Mutation to create a node.  Invalidates the node list and the active project graph. */
export function useCreateNode() {
  const queryClient = useQueryClient();
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  return useMutation<AppNode, Error, Partial<AppNode>>({
    mutationFn: (payload) => createNode(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nodes"] });
      if (activeProjectId) {
        queryClient.invalidateQueries({
          queryKey: ["projectGraph", activeProjectId],
        });
      }
    },
  });
}

/** Mutation to update a node.  Invalidates the specific node query. */
export function useUpdateNode() {
  const queryClient = useQueryClient();
  return useMutation<AppNode, Error, { id: string; payload: Partial<AppNode> }>({
    mutationFn: ({ id, payload }) => updateNode(id, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["node", variables.id] });
    },
  });
}

/** Mutation to delete a node.  Invalidates the node list. */
export function useDeleteNode() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => deleteNode(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nodes"] });
    },
  });
}
