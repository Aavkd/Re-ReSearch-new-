import { useQuery } from "@tanstack/react-query";
import { search } from "../api/library";
import type { AppNode, SearchMode } from "../types";

/**
 * TanStack Query wrapper for `GET /search`.
 *
 * - Only fires when `query` is longer than 1 character.
 * - `staleTime: 0` — search results are always considered stale so re-typing
 *   triggers a fresh request.
 */
export function useSearch(
  query: string,
  mode: SearchMode = "hybrid",
  topK?: number
) {
  return useQuery<AppNode[]>({
    queryKey: ["search", query, mode, topK],
    queryFn: () => search(query, mode, topK),
    enabled: query.length > 1,
    staleTime: 0,
  });
}
