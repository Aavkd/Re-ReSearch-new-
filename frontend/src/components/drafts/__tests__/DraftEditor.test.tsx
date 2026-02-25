import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DraftEditor } from "../DraftEditor";
import type { ArtifactNode } from "../../../types";

// ── Mock CodeMirror (no DOM canvas support in jsdom) ─────────────────────────
//
// We capture the `doc` string passed to EditorState.create so we can assert
// it matches `metadata.content_body`.

let capturedDoc = "";

vi.mock("@codemirror/lang-markdown", () => ({
  markdown: () => [],
}));

vi.mock("@codemirror/view", () => {
  const MockEditorView = vi.fn().mockImplementation(
    ({ state, parent }: { state: { doc: string }; parent: HTMLElement }) => {
      // Write the initial doc text into the container so we can query it
      if (parent && state?.doc) {
        const el = document.createElement("div");
        el.textContent = state.doc;
        el.setAttribute("data-testid", "cm-doc");
        parent.appendChild(el);
      }
      return { destroy: vi.fn() };
    }
  );
  // Static methods used as extensions
  (MockEditorView as unknown as Record<string, unknown>).domEventHandlers =
    vi.fn(() => []);
  (MockEditorView as unknown as Record<string, unknown>).theme = vi.fn(() => []);

  return {
    EditorView: MockEditorView,
    keymap: { of: vi.fn(() => []) },
    lineNumbers: vi.fn(() => []),
    highlightActiveLine: vi.fn(() => []),
  };
});

vi.mock("@codemirror/state", () => ({
  EditorState: {
    create: vi.fn(({ doc }: { doc: string }) => {
      capturedDoc = doc ?? "";
      return { doc };
    }),
  },
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const nodeWithContent: ArtifactNode = {
  id: "art-1",
  node_type: "Artifact",
  title: "My Draft",
  content_path: null,
  metadata: { content_body: "# Hello World\n\nSome content here." },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const nodeEmpty: ArtifactNode = {
  id: "art-2",
  node_type: "Artifact",
  title: "Empty Draft",
  content_path: null,
  metadata: {},
  created_at: 1700000001,
  updated_at: 1700000001,
};

// ── Tests ─────────────────────────────────────────────────────────────────────

afterEach(() => {
  capturedDoc = "";
  vi.clearAllMocks();
});

describe("DraftEditor", () => {
  it("loads initial content from metadata.content_body", () => {
    render(
      <MemoryRouter>
        <DraftEditor node={nodeWithContent} onSave={vi.fn()} />
      </MemoryRouter>
    );
    expect(capturedDoc).toBe("# Hello World\n\nSome content here.");
  });

  it("uses empty string when metadata.content_body is absent", () => {
    render(
      <MemoryRouter>
        <DraftEditor node={nodeEmpty} onSave={vi.fn()} />
      </MemoryRouter>
    );
    expect(capturedDoc).toBe("");
  });

  it("renders the editor container", () => {
    render(
      <MemoryRouter>
        <DraftEditor node={nodeWithContent} onSave={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByTestId("draft-editor")).toBeInTheDocument();
    expect(screen.getByTestId("cm-container")).toBeInTheDocument();
  });
});
