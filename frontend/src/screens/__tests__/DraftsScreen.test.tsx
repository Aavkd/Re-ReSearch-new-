import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { DraftsScreen } from "../DraftsScreen";
import { useProjectStore } from "../../stores/projectStore";
import { apiClient } from "../../api/client";
import type { ArtifactNode } from "../../types";

// ── Mock DraftEditor to avoid CodeMirror DOM requirements ─────────────────────
//
// The mock exposes a <textarea> that fires `onSave` on blur and Ctrl+S so that
// screen-level tests can verify the PUT call without depending on CodeMirror internals.

vi.mock("../../components/drafts/DraftEditor", () => ({
  DraftEditor: ({
    node,
    onSave,
  }: {
    node: ArtifactNode;
    onSave: (content: string) => void;
  }) => (
    <div data-testid="draft-editor">
      <textarea
        data-testid="editor-textarea"
        defaultValue={
          typeof node.metadata.content_body === "string"
            ? node.metadata.content_body
            : ""
        }
        onBlur={(e) => onSave(e.target.value)}
        onKeyDown={(e) => {
          if (e.ctrlKey && e.key === "s") {
            onSave((e.target as HTMLTextAreaElement).value);
          }
        }}
      />
    </div>
  ),
}));

// ── Constants ─────────────────────────────────────────────────────────────────

const BASE = "http://localhost:8000";
apiClient.defaults.baseURL = BASE;

const PROJECT_ID = "proj-1";

const ARTIFACT: ArtifactNode = {
  id: "art-1",
  node_type: "Artifact",
  title: "My Draft",
  content_path: null,
  metadata: { content_body: "Hello world" },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const NEW_ARTIFACT: ArtifactNode = {
  id: "art-new",
  node_type: "Artifact",
  title: "New Draft",
  content_path: null,
  metadata: {},
  created_at: 1700000001,
  updated_at: 1700000001,
};

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get(`${BASE}/nodes`, ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("type") === "Artifact") {
      return HttpResponse.json([ARTIFACT]);
    }
    return HttpResponse.json([]);
  }),
  http.get(`${BASE}/nodes/${ARTIFACT.id}`, () => HttpResponse.json(ARTIFACT)),
  http.get(`${BASE}/nodes/${NEW_ARTIFACT.id}`, () =>
    HttpResponse.json(NEW_ARTIFACT)
  ),
  http.get(`${BASE}/projects/${PROJECT_ID}/graph`, () =>
    HttpResponse.json({ nodes: [ARTIFACT], edges: [] })
  ),
  http.post(`${BASE}/nodes`, () =>
    HttpResponse.json(NEW_ARTIFACT, { status: 201 })
  ),
  http.post(`${BASE}/projects/${PROJECT_ID}/link`, () =>
    HttpResponse.json({}, { status: 200 })
  ),
  http.put(`${BASE}/nodes/${ARTIFACT.id}`, () => HttpResponse.json(ARTIFACT)),
  http.put(`${BASE}/nodes/${NEW_ARTIFACT.id}`, () =>
    HttpResponse.json(NEW_ARTIFACT)
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Reset Zustand ─────────────────────────────────────────────────────────────

beforeEach(() => {
  useProjectStore.setState({
    activeProjectId: PROJECT_ID,
    activeProjectName: "Test Project",
  });
});

// ── Render helper ─────────────────────────────────────────────────────────────

function renderDrafts(initialEntry = "/drafts") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="drafts" element={<DraftsScreen />} />
          <Route path="drafts/:nodeId" element={<DraftsScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { qc };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("DraftsScreen", () => {
  it("renders split layout — both panels present", async () => {
    renderDrafts();
    expect(screen.getByTestId("drafts-screen")).toBeInTheDocument();
    expect(screen.getByTestId("draft-list")).toBeInTheDocument();
    expect(screen.getByTestId("no-draft-selected")).toBeInTheDocument();
  });

  it("shows no-project guard when no project is active", () => {
    useProjectStore.setState({ activeProjectId: null, activeProjectName: null });
    renderDrafts();
    expect(
      screen.getByText(/select a project in the sidebar/i)
    ).toBeInTheDocument();
  });

  it("selects draft from URL :nodeId param", async () => {
    renderDrafts(`/drafts/${ARTIFACT.id}`);
    await waitFor(
      () => expect(screen.getByTestId("draft-editor")).toBeInTheDocument(),
      { timeout: 3000 }
    );
  });

  it("new draft modal opens on '+ New Draft' click", async () => {
    renderDrafts();
    await waitFor(() =>
      expect(screen.getByTestId("new-draft-btn")).toBeInTheDocument()
    );
    fireEvent.click(screen.getByTestId("new-draft-btn"));
    expect(screen.getByTestId("new-draft-modal")).toBeInTheDocument();
  });

  it("new draft modal creates and selects the new node", async () => {
    const user = userEvent.setup();
    renderDrafts();
    await waitFor(() =>
      expect(screen.getByTestId("new-draft-btn")).toBeInTheDocument()
    );
    fireEvent.click(screen.getByTestId("new-draft-btn"));
    await user.type(screen.getByTestId("draft-title-input"), "New Draft");
    fireEvent.click(screen.getByTestId("create-btn"));
    await waitFor(
      () => expect(screen.getByTestId("draft-editor")).toBeInTheDocument(),
      { timeout: 3000 }
    );
  });

  it("auto-save on blur triggers PUT /nodes/{id}", async () => {
    const putCalls: string[] = [];
    server.use(
      http.put(`${BASE}/nodes/:id`, ({ params }) => {
        putCalls.push(params.id as string);
        return HttpResponse.json(ARTIFACT);
      })
    );

    renderDrafts(`/drafts/${ARTIFACT.id}`);
    await waitFor(
      () => expect(screen.getByTestId("editor-textarea")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    fireEvent.blur(screen.getByTestId("editor-textarea"));
    await waitFor(() => expect(putCalls).toContain(ARTIFACT.id), {
      timeout: 3000,
    });
  });

  it("Ctrl+S triggers save (PUT /nodes/{id})", async () => {
    const putCalls: string[] = [];
    server.use(
      http.put(`${BASE}/nodes/:id`, ({ params }) => {
        putCalls.push(params.id as string);
        return HttpResponse.json(ARTIFACT);
      })
    );

    renderDrafts(`/drafts/${ARTIFACT.id}`);
    await waitFor(
      () => expect(screen.getByTestId("editor-textarea")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    fireEvent.keyDown(screen.getByTestId("editor-textarea"), {
      key: "s",
      ctrlKey: true,
    });
    await waitFor(() => expect(putCalls).toContain(ARTIFACT.id), {
      timeout: 3000,
    });
  });
});
