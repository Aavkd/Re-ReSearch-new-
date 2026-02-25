import { useQuery } from "@tanstack/react-query";
import { fetchProjectGraph } from "../api/projects";
import type { ProjectGraph } from "../types";

/**
 * React-Flow–ready project subgraph (nodes + edges).
 *
 * Stale after 30 s to catch new ingest without forcing a manual refresh.
 * Only fetches when `id` is non-null / non-empty.
 */
export function useProjectGraph(id: string | null) {
  return useQuery<ProjectGraph>({
    queryKey: ["projectGraph", id],
    queryFn: () => fetchProjectGraph(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}
