import { useState, useMemo } from "react";
import { useProjectStore } from "../stores/projectStore";
import { useProjectGraph } from "../hooks/useProjectGraph";
import { GraphCanvas } from "../components/map/GraphCanvas";
import { NodeDetailPanel } from "../components/map/NodeDetailPanel";
import type { AppNode } from "../types";

// ── Node-type legend config ───────────────────────────────────────────────

const NODE_TYPE_LEGEND = [
  { type: "Project", label: "Project", color: "bg-purple-400" },
  { type: "Source",   label: "Source",  color: "bg-blue-400"   },
  { type: "Artifact", label: "Artifact",color: "bg-emerald-400"},
] as const;

/**
 * Map screen — interactive React Flow canvas for the active project.
 *
 * States:
 *   - No project selected: prompt to select one.
 *   - Loading: centred spinner.
 *   - Error: error message with retry button.
 *   - Loaded: GraphCanvas + NodeDetailPanel overlay + type-filter legend.
 */
export function MapScreen() {
  const [selectedNode, setSelectedNode] = useState<AppNode | null>(null);
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());

  const toggleType = (type: string) =>
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      next.has(type) ? next.delete(type) : next.add(type);
      return next;
    });

  const { activeProjectId, activeProjectName } = useProjectStore();
  const {
    data: graphData,
    isLoading,
    isError,
    refetch,
  } = useProjectGraph(activeProjectId);

  // ── Filtered graph data (all hooks must be above early returns) ────────
  const rawData = graphData ?? { nodes: [], edges: [] };
  const data = useMemo(() => {
    if (hiddenTypes.size === 0) return rawData;
    const visibleNodes = rawData.nodes.filter(
      (n) => !hiddenTypes.has(n.node_type)
    );
    const visibleIds = new Set(visibleNodes.map((n) => n.id));
    const visibleEdges = rawData.edges.filter(
      (e) => visibleIds.has(e.source_id) && visibleIds.has(e.target_id)
    );
    return { nodes: visibleNodes, edges: visibleEdges };
  }, [rawData, hiddenTypes]);

  // ── No project ─────────────────────────────────────────────────────────
  if (!activeProjectId) {
    return (
      <div
        className="flex flex-1 items-center justify-center text-sm text-gray-400"
        data-testid="map-screen"
      >
        Select a project to view its map.
      </div>
    );
  }

  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        className="flex flex-1 items-center justify-center"
        data-testid="map-screen"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div
        className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-red-600"
        data-testid="map-screen"
      >
        <p>Failed to load graph.</p>
        <button
          onClick={() => refetch()}
          className="rounded bg-red-100 px-3 py-1 hover:bg-red-200"
        >
          Retry?
        </button>
      </div>
    );
  }

  return (
    <div
      className="relative flex flex-1 flex-col overflow-hidden"
      data-testid="map-screen"
    >
      {/* ── Toolbar ───────────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2">
        <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-100">
          Map — {activeProjectName}
        </h1>
        <button
          onClick={() => refetch()}
          className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          title="Refresh graph"
        >
          ↺ Refresh
        </button>
      </div>

      {/* ── Canvas area ───────────────────────────────────────────────── */}
      <div className="relative flex-1">
        <GraphCanvas graphData={data} onNodeClick={setSelectedNode} />

        {/* ── Legend / type filter (bottom-left) ─────────────────────── */}
        <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-gray-200 dark:border-gray-700 bg-white/90 dark:bg-gray-900/90 px-3 py-2 shadow-sm backdrop-blur-sm">
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
            Filter
          </p>
          <div className="flex flex-col gap-1">
            {NODE_TYPE_LEGEND.map(({ type, label, color }) => {
              const hidden = hiddenTypes.has(type);
              return (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={`flex items-center gap-2 rounded px-1.5 py-0.5 text-xs transition-opacity ${
                    hidden ? "opacity-40" : ""
                  } hover:bg-gray-100 dark:hover:bg-gray-800`}
                  title={hidden ? `Show ${label} nodes` : `Hide ${label} nodes`}
                  data-testid={`legend-toggle-${type.toLowerCase()}`}
                >
                  <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
                  <span className="text-gray-700 dark:text-gray-300">{label}</span>
                  {hidden && (
                    <span className="text-gray-400 dark:text-gray-500">(hidden)</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
}
