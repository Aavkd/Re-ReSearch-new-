import { useState } from "react";
import { useProjectStore } from "../stores/projectStore";
import { useProjectGraph } from "../hooks/useProjectGraph";
import { GraphCanvas } from "../components/map/GraphCanvas";
import { NodeDetailPanel } from "../components/map/NodeDetailPanel";
import type { AppNode } from "../types";

/**
 * Map screen — interactive React Flow canvas for the active project.
 *
 * States:
 *   - No project selected: prompt to select one.
 *   - Loading: centred spinner.
 *   - Error: error message with retry button.
 *   - Loaded: GraphCanvas + NodeDetailPanel overlay.
 */
export function MapScreen() {
  const [selectedNode, setSelectedNode] = useState<AppNode | null>(null);

  const { activeProjectId, activeProjectName } = useProjectStore();
  const {
    data: graphData,
    isLoading,
    isError,
    refetch,
  } = useProjectGraph(activeProjectId);

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

  const data = graphData ?? { nodes: [], edges: [] };

  return (
    <div
      className="relative flex flex-1 flex-col overflow-hidden"
      data-testid="map-screen"
    >
      {/* ── Toolbar ───────────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
        <h1 className="text-sm font-semibold text-gray-800">
          Map — {activeProjectName}
        </h1>
        <button
          onClick={() => refetch()}
          className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
          title="Refresh graph"
        >
          ↺ Refresh
        </button>
      </div>

      {/* ── Canvas area ───────────────────────────────────────────────── */}
      <div className="relative flex-1">
        <GraphCanvas graphData={data} onNodeClick={setSelectedNode} />
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
}
