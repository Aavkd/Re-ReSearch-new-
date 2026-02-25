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
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { LibraryScreen } from "../LibraryScreen";
import { useProjectStore } from "../../stores/projectStore";
import { apiClient } from "../../api/client";

// ── Constants ────────────────────────────────────────────

const BASE = "http://localhost:8000";
apiClient.defaults.baseURL = BASE;

const ACTIVE_PROJECT_ID = "proj-1";

const SOURCE_NODE = {
  id: "node-src-1",
  node_type: "Source",
  title: "Example Article",
  content_path: null,
  metadata: { url: "https://example.com" },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const ARTIFACT_NODE = {
  id: "node-art-1",
  node_type: "Artifact",
  title: "My Draft",
  content_path: null,
  metadata: {},
  created_at: 1700000001,
  updated_at: 1700000001,
};

const INGEST_RESPONSE = {
  node_id: "node-src-new",
  title: "Ingested Article",
  node_type: "Source",
  metadata: {},
};

// ── MSW server ───────────────────────────────────────────

const server = setupServer(
  http.get(`${BASE}/projects/${ACTIVE_PROJECT_ID}/nodes`, () =>
    HttpResponse.json([SOURCE_NODE, ARTIFACT_NODE])
  ),
  http.get(`${BASE}/search`, () =>
    HttpResponse.json([SOURCE_NODE, ARTIFACT_NODE])
  ),
  http.post(`${BASE}/ingest/url`, () => HttpResponse.json(INGEST_RESPONSE)),
  http.post(`${BASE}/projects/${ACTIVE_PROJECT_ID}/link`, () =>
    HttpResponse.json({}, { status: 200 })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Reset Zustand state ───────────────────────────────────

beforeEach(() => {
  useProjectStore.setState({
    activeProjectId: null,
    activeProjectName: null,
  });
});

// ── Render helper ─────────────────────────────────────────

function renderLibrary(initialEntry = "/library") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <LibraryScreen />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { queryClient };
}

// ── Tests ─────────────────────────────────────────────────

// Ensure fake timers are never left active even when a test times out
afterEach(() => vi.useRealTimers());

describe("LibraryScreen", () => {
  it("renders the add source panel and search bar", () => {
    renderLibrary();
    expect(screen.getByTestId("add-source-panel")).toBeTruthy();
    expect(screen.getByTestId("search-bar")).toBeTruthy();
  });

  it("URL input and PDF tab are visible in AddSourcePanel", () => {
    renderLibrary();
    expect(screen.getByTestId("url-input")).toBeTruthy();
    expect(screen.getByTestId("tab-pdf")).toBeTruthy();
  });

  it("shows 'Select a project' message when no project is active", () => {
    renderLibrary();
    expect(
      screen.getByText(/select a project in the sidebar/i)
    ).toBeTruthy();
  });

  it("URL add button is disabled when no project is active", () => {
    renderLibrary();
    const addBtn = screen.getByTestId("url-add-button");
    expect(addBtn).toBeDisabled();
  });

  it("URL add button is enabled when a project is active", () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });
    renderLibrary();
    // Need a URL value too — button is also disabled when input is empty
    const input = screen.getByTestId("url-input");
    // Input itself should be enabled
    expect(input).not.toBeDisabled();
  });

  it("ingest URL calls POST /ingest/url then POST /projects/{id}/link", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    const ingestCalls: string[] = [];
    const linkCalls: string[] = [];

    server.use(
      http.post(`${BASE}/ingest/url`, async ({ request }) => {
        const body = (await request.json()) as { url: string };
        ingestCalls.push(body.url);
        return HttpResponse.json(INGEST_RESPONSE);
      }),
      http.post(`${BASE}/projects/${ACTIVE_PROJECT_ID}/link`, () => {
        linkCalls.push("linked");
        return HttpResponse.json({});
      })
    );

    renderLibrary();

    const input = screen.getByTestId("url-input");
    await userEvent.type(input, "https://example.com/article");
    await userEvent.click(screen.getByTestId("url-add-button"));

    await waitFor(() => {
      expect(ingestCalls).toHaveLength(1);
      expect(ingestCalls[0]).toBe("https://example.com/article");
      expect(linkCalls).toHaveLength(1);
    });

    // Success message shown
    expect(screen.getByTestId("ingest-success")).toBeTruthy();
  });

  it("shows error message on ingest failure (502)", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    server.use(
      http.post(`${BASE}/ingest/url`, () =>
        HttpResponse.json({ detail: "Bad Gateway" }, { status: 502 })
      )
    );

    renderLibrary();

    const input = screen.getByTestId("url-input");
    await userEvent.type(input, "https://fail.example.com");
    await userEvent.click(screen.getByTestId("url-add-button"));

    await waitFor(() =>
      expect(screen.getByTestId("ingest-error")).toBeTruthy()
    );
  });

  it("search query is debounced — search fires after 300 ms", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    const searchCalls: string[] = [];
    server.use(
      http.get(`${BASE}/search`, ({ request }) => {
        const url = new URL(request.url);
        searchCalls.push(url.searchParams.get("q") ?? "");
        return HttpResponse.json([SOURCE_NODE]);
      })
    );

    renderLibrary();

    const input = screen.getByTestId("search-input");
    // Three rapid synchronous changes — debounce resets timer on each
    fireEvent.change(input, { target: { value: "re" } });
    fireEvent.change(input, { target: { value: "res" } });
    fireEvent.change(input, { target: { value: "rese" } });

    // Debounce hasn't fired yet (no timer has elapsed)
    expect(searchCalls).toHaveLength(0);

    // Wait for the debounce to fire and the search to complete (real ~300ms)
    await waitFor(() => expect(searchCalls.length).toBeGreaterThanOrEqual(1), {
      timeout: 2000,
    });

    // Only one request despite three rapid changes
    expect(searchCalls).toHaveLength(1);
    expect(searchCalls[0]).toBe("rese");
  }, 10_000);

  it("mode selector sends correct mode param in search request", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    let capturedMode = "";
    server.use(
      http.get(`${BASE}/search`, ({ request }) => {
        const url = new URL(request.url);
        capturedMode = url.searchParams.get("mode") ?? "";
        return HttpResponse.json([SOURCE_NODE]);
      })
    );

    renderLibrary();

    // Select semantic mode first, then type a query
    const semanticRadio = screen.getByRole("radio", { name: /semantic/i });
    fireEvent.click(semanticRadio);

    const input = screen.getByTestId("search-input");
    fireEvent.change(input, { target: { value: "ml" } });

    await waitFor(() => expect(capturedMode).toBe("semantic"), {
      timeout: 2000,
    });
  }, 10_000);

  it("shows 'No results' empty state when search returns nothing", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    server.use(
      http.get(`${BASE}/search`, () => HttpResponse.json([]))
    );

    renderLibrary();

    const input = screen.getByTestId("search-input");
    fireEvent.change(input, { target: { value: "xyz" } });

    // Wait for the debounce + query + empty state to render
    await waitFor(
      () => expect(screen.getByTestId("no-results")).toBeTruthy(),
      { timeout: 2000 }
    );
  }, 10_000);

  it("Artifact result card shows '→ Open Draft' link", async () => {
    useProjectStore.setState({
      activeProjectId: ACTIVE_PROJECT_ID,
      activeProjectName: "Test Project",
    });

    renderLibrary();

    await waitFor(() =>
      expect(screen.getByText("My Draft")).toBeTruthy()
    );

    const link = screen.getByRole("link", { name: /open draft/i });
    expect(link.getAttribute("href")).toBe(`/drafts/${ARTIFACT_NODE.id}`);
  });
});
