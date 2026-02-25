import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { GraphCanvas } from "../GraphCanvas";
import type { ProjectGraph, AppNode } from "../../../types";

// ── Mock @xyflow/react (requires canvas / WebGL not available in jsdom) ─────

vi.mock("@xyflow/react", () => ({
  ReactFlow: ({
    nodes,
    onNodeClick,
  }: {
    nodes: Array<{ id: string; data: { label: string; raw: AppNode } }>;
    onNodeClick: (ev: unknown, node: { id: string; data: { label: string; raw: AppNode } }) => void;
  }) => (
    <div data-testid="react-flow">
      {nodes.map((n) => (
        <div
          key={n.id}
          data-testid={`rf-node-${n.id}`}
          onClick={() => onNodeClick(undefined, n)}
        >
          {n.data.label}
        </div>
      ))}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  MarkerType: { ArrowClosed: "arrowclosed" },
}));

// ── Mock @dagrejs/dagre (no-op layout — positions all nodes at 0,0) ──────────

vi.mock("@dagrejs/dagre", () => {
  const nodes: Record<string, { x: number; y: number; width: number; height: number }> = {};
  const Graph = vi.fn().mockImplementation(() => ({
    setDefaultEdgeLabel: vi.fn().mockReturnThis(),
    setGraph: vi.fn(),
    setNode: vi.fn((id: string, opts: { width: number; height: number }) => {
      nodes[id] = { x: 0, y: 0, ...opts };
    }),
    setEdge: vi.fn(),
    hasNode: vi.fn((id: string) => id in nodes),
    node: vi.fn((id: string) => nodes[id] ?? { x: 0, y: 0 }),
  }));
  return {
    default: {
      graphlib: { Graph },
      layout: vi.fn(),
    },
  };
});

// Also mock the css import
vi.mock("@xyflow/react/dist/style.css", () => ({}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const source: AppNode = {
  id: "src-1",
  node_type: "Source",
  title: "Source Article",
  content_path: null,
  metadata: { url: "https://example.com" },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const artifact: AppNode = {
  id: "art-1",
  node_type: "Artifact",
  title: "My Draft",
  content_path: null,
  metadata: {},
  created_at: 1700000001,
  updated_at: 1700000001,
};

const emptyGraph: ProjectGraph = { nodes: [], edges: [] };
const populatedGraph: ProjectGraph = {
  nodes: [source, artifact],
  edges: [
    { source_id: "src-1", target_id: "art-1", relation_type: "DERIVED_FROM", created_at: 1700000002 },
  ],
};

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("GraphCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no nodes", () => {
    wrap(<GraphCanvas graphData={emptyGraph} onNodeClick={vi.fn()} />);
    expect(screen.getByTestId("graph-empty")).toBeInTheDocument();
    expect(screen.getByText(/no nodes in this project yet/i)).toBeInTheDocument();
  });

  it("renders nodes correctly", () => {
    wrap(<GraphCanvas graphData={populatedGraph} onNodeClick={vi.fn()} />);
    expect(screen.getByTestId("rf-node-src-1")).toBeInTheDocument();
    expect(screen.getByTestId("rf-node-art-1")).toBeInTheDocument();
    expect(screen.getByText("Source Article")).toBeInTheDocument();
    expect(screen.getByText("My Draft")).toBeInTheDocument();
  });

  it("onNodeClick fires with correct node data", () => {
    const handler = vi.fn();
    wrap(<GraphCanvas graphData={populatedGraph} onNodeClick={handler} />);
    fireEvent.click(screen.getByTestId("rf-node-src-1"));
    expect(handler).toHaveBeenCalledWith(source);
  });
});
