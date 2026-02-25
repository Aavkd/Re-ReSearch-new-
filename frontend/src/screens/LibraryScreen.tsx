import { useState, useMemo } from "react";
import { AddSourcePanel } from "../components/library/AddSourcePanel";
import { SearchBar } from "../components/library/SearchBar";
import { NodeResultCard } from "../components/library/NodeResultCard";
import { useSearch } from "../hooks/useSearch";
import { useProjectNodes } from "../hooks/useProjects";
import { useProjectStore } from "../stores/projectStore";
import type { SearchMode } from "../types";

/**
 * Library screen — ingest sources and search the knowledge base.
 *
 * Layout:
 *   <AddSourcePanel />   — URL / PDF ingest
 *   <SearchBar />        — debounced query + mode selector
 *   Results list         — project-scoped node cards
 *
 * Search scoping strategy:
 *  - When query is empty: show all nodes belonging to the active project
 *    (GET /projects/{id}/nodes).
 *  - When query is active: use GET /search (global) but filter the results
 *    client-side to nodes that belong to the active project by id.
 *
 * TODO: GET /search has no project_id filter param.  Once the backend adds
 * scoped search, remove the client-side filtering below and pass project_id
 * directly to the search endpoint.
 */
export function LibraryScreen() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");

  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  // Project nodes — shown when search query is empty
  const {
    data: projectNodes,
    isLoading: projectNodesLoading,
  } = useProjectNodes(activeProjectId);

  // Search results — shown when query has > 1 char
  const {
    data: searchResults,
    isFetching: searchFetching,
  } = useSearch(query, mode);

  // Build a Set of node IDs belonging to the active project for client-side filtering
  const projectNodeIds = useMemo(
    () => new Set((projectNodes ?? []).map((n) => n.id)),
    [projectNodes]
  );

  const isSearchActive = query.length > 1;

  const displayNodes = useMemo(() => {
    if (!isSearchActive) {
      return projectNodes ?? [];
    }
    // Filter search results to the active project's node id set when project is active
    if (activeProjectId && projectNodeIds.size > 0) {
      return (searchResults ?? []).filter((n) => projectNodeIds.has(n.id));
    }
    return searchResults ?? [];
  }, [isSearchActive, projectNodes, searchResults, activeProjectId, projectNodeIds]);

  const isLoading = isSearchActive ? searchFetching : projectNodesLoading;

  if (!activeProjectId) {
    return (
      <div
        className="flex flex-1 flex-col gap-4 p-6"
        data-testid="library-screen"
      >
        <AddSourcePanel />
        <SearchBar
          onChange={({ query: q, mode: m }) => {
            setQuery(q);
            setMode(m);
          }}
        />
        <div className="flex flex-1 items-center justify-center text-sm text-gray-400">
          Select a project in the sidebar to get started.
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 flex-col gap-4 p-6"
      data-testid="library-screen"
    >
      <AddSourcePanel />

      <SearchBar
        onChange={({ query: q, mode: m }) => {
          setQuery(q);
          setMode(m);
        }}
      />

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3" data-testid="results-skeleton">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-16 animate-pulse rounded-lg bg-gray-100"
            />
          ))}
        </div>
      )}

      {/* Empty state — only shown once a search query has been entered */}
      {!isLoading && isSearchActive && displayNodes.length === 0 && (
        <p className="text-center text-sm text-gray-400" data-testid="no-results">
          No results
        </p>
      )}

      {/* Results list */}
      {!isLoading && displayNodes.length > 0 && (
        <ul className="space-y-3" data-testid="results-list">
          {displayNodes.map((node) => (
            <li key={node.id}>
              <NodeResultCard node={node} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
