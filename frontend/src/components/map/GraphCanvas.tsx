import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Node as RFNode,
  type Edge as RFEdge,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Dagre from "@dagrejs/dagre";
import { ProjectNode } from "./customNodes/ProjectNode";
import { SourceNode } from "./customNodes/SourceNode";
import { ArtifactNode } from "./customNodes/ArtifactNode";
import type { ProjectGraph, AppNode, Edge as BackendEdge } from "../../types";

// ── Custom node type registry ─────────────────────────────────────────────

const nodeTypes = {
  projectNode: ProjectNode,
  sourceNode: SourceNode,
  artifactNode: ArtifactNode,
};

// ── Dagre layout helper ───────────────────────────────────────────────────

function computeLayout(
  nodes: AppNode[],
  edges: BackendEdge[],
  direction: "LR" | "TB"
): { rfNodes: RFNode[]; rfEdges: RFEdge[] } {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, marginx: 30, marginy: 30 });

  nodes.forEach((n) => g.setNode(n.id, { width: 180, height: 56 }));
  edges.forEach((e) => {
    // Only add edges whose endpoints exist in node list
    if (g.hasNode(e.source_id) && g.hasNode(e.target_id)) {
      g.setEdge(e.source_id, e.target_id);
    }
  });

  Dagre.layout(g);

  const rfNodes: RFNode[] = nodes.map((n) => {
    const pos = g.node(n.id) ?? { x: 0, y: 0 };
    const rfType =
      n.node_type === "Project"
        ? "projectNode"
        : n.node_type === "Source"
          ? "sourceNode"
          : "artifactNode";
    return {
      id: n.id,
      type: rfType,
      position: { x: pos.x, y: pos.y },
      data: { label: n.title, raw: n },
    };
  });

  const rfEdges: RFEdge[] = edges.map((e) => ({
    id: `${e.source_id}-${e.target_id}-${e.relation_type}`,
    source: e.source_id,
    target: e.target_id,
    label: e.relation_type,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  return { rfNodes, rfEdges };
}

// ── Component ─────────────────────────────────────────────────────────────

interface GraphCanvasProps {
  graphData: ProjectGraph;
  onNodeClick: (node: AppNode) => void;
}

/**
 * React Flow canvas for the active project graph.
 *
 * - Converts backend nodes/edges to React Flow format with dagre auto-layout.
 * - Layout direction: LR when > 10 nodes, TB otherwise.
 * - Empty state when no nodes.
 */
export function GraphCanvas({ graphData, onNodeClick }: GraphCanvasProps) {
  const direction = graphData.nodes.length > 10 ? "LR" : "TB";

  const { rfNodes, rfEdges } = useMemo(
    () => computeLayout(graphData.nodes, graphData.edges, direction),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(graphData)]
  );

  if (graphData.nodes.length === 0) {
    return (
      <div
        className="flex h-full items-center justify-center text-sm text-gray-400"
        data-testid="graph-empty"
      >
        No nodes in this project yet.
      </div>
    );
  }

  const handleNodeClick: NodeMouseHandler = (_event, rfNode) => {
    const raw = (rfNode.data as { raw: AppNode }).raw;
    onNodeClick(raw);
  };

  return (
    <div className="h-full w-full" data-testid="graph-canvas">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-right"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
