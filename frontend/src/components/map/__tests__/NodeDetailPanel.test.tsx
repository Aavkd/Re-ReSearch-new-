import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { NodeDetailPanel } from "../NodeDetailPanel";
import type { AppNode } from "../../../types";

const sourceNode: AppNode = {
  id: "src-1",
  node_type: "Source",
  title: "Source Article",
  content_path: null,
  metadata: { url: "https://example.com" },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const artifactNode: AppNode = {
  id: "art-1",
  node_type: "Artifact",
  title: "My Draft",
  content_path: null,
  metadata: {},
  created_at: 1700000001,
  updated_at: 1700000001,
};

const projectNode: AppNode = {
  id: "proj-1",
  node_type: "Project",
  title: "Test Project",
  content_path: null,
  metadata: {},
  created_at: 1700000002,
  updated_at: 1700000002,
};

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("NodeDetailPanel", () => {
  it("renders nothing when node is null", () => {
    const { container } = wrap(
      <NodeDetailPanel node={null} onClose={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows node title and type badge", () => {
    wrap(<NodeDetailPanel node={sourceNode} onClose={vi.fn()} />);
    expect(screen.getByText("Source Article")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
  });

  it("shows URL link for Source node with metadata.url", () => {
    wrap(<NodeDetailPanel node={sourceNode} onClose={vi.fn()} />);
    const link = screen.getByTestId("meta-url");
    expect(link).toHaveAttribute("href", "https://example.com");
  });

  it("hides 'Open Draft' link for Source node", () => {
    wrap(<NodeDetailPanel node={sourceNode} onClose={vi.fn()} />);
    expect(screen.queryByTestId("open-draft-link")).not.toBeInTheDocument();
  });

  it("shows 'Open Draft' link for Artifact node", () => {
    wrap(<NodeDetailPanel node={artifactNode} onClose={vi.fn()} />);
    const link = screen.getByTestId("open-draft-link");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/drafts/art-1");
  });

  it("calls onClose when × button is clicked", () => {
    const onClose = vi.fn();
    wrap(<NodeDetailPanel node={projectNode} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("panel-close"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
