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
import { ProjectSwitcher } from "../ProjectSwitcher";
import { useProjectStore } from "../../../stores/projectStore";
import { apiClient } from "../../../api/client";

// ── Constants ────────────────────────────────────────────

const BASE = "http://localhost:8000";
apiClient.defaults.baseURL = BASE;

const PROJECTS = [
  {
    id: "proj-1",
    node_type: "Project",
    title: "Alpha Project",
    content_path: null,
    metadata: {},
    created_at: 1700000000,
    updated_at: 1700000000,
  },
  {
    id: "proj-2",
    node_type: "Project",
    title: "Beta Project",
    content_path: null,
    metadata: {},
    created_at: 1700000001,
    updated_at: 1700000001,
  },
];

const NEW_PROJECT = {
  id: "proj-3",
  node_type: "Project",
  title: "Gamma Project",
  content_path: null,
  metadata: {},
  created_at: 1700000002,
  updated_at: 1700000002,
};

// ── MSW server ───────────────────────────────────────────

const server = setupServer(
  http.get(`${BASE}/projects`, () => HttpResponse.json(PROJECTS)),
  http.post(`${BASE}/projects`, () =>
    HttpResponse.json(NEW_PROJECT, { status: 201 })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Reset Zustand store before each test ─────────────────

beforeEach(() => {
  useProjectStore.setState({
    activeProjectId: null,
    activeProjectName: null,
  });
});

// ── Render helper ────────────────────────────────────────

function renderSwitcher() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProjectSwitcher />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { queryClient };
}

// ── Tests ────────────────────────────────────────────────

describe("ProjectSwitcher", () => {
  it("shows 'No project selected' when store has no active project", () => {
    renderSwitcher();
    expect(screen.getByText("No project selected")).toBeTruthy();
  });

  it("shows active project name from Zustand store", () => {
    useProjectStore.setState({
      activeProjectId: "proj-1",
      activeProjectName: "Alpha Project",
    });
    renderSwitcher();
    expect(screen.getByTestId("project-switcher-trigger").textContent).toContain(
      "Alpha Project"
    );
  });

  it("dropdown lists all projects on trigger click", async () => {
    renderSwitcher();
    await userEvent.click(screen.getByTestId("project-switcher-trigger"));

    await waitFor(() => {
      expect(screen.getByText("Alpha Project")).toBeTruthy();
      expect(screen.getByText("Beta Project")).toBeTruthy();
    });
  });

  it("selecting a project updates the Zustand store and closes dropdown", async () => {
    renderSwitcher();
    await userEvent.click(screen.getByTestId("project-switcher-trigger"));

    await waitFor(() => screen.getByText("Alpha Project"));
    await userEvent.click(screen.getByText("Alpha Project"));

    const state = useProjectStore.getState();
    expect(state.activeProjectId).toBe("proj-1");
    expect(state.activeProjectName).toBe("Alpha Project");

    // Dropdown should close
    expect(screen.queryByTestId("project-dropdown")).toBeNull();
  });

  it("opens NewProjectModal when '+ New Project' is clicked", async () => {
    renderSwitcher();
    await userEvent.click(screen.getByTestId("project-switcher-trigger"));
    await waitFor(() => screen.getByTestId("new-project-button"));
    await userEvent.click(screen.getByTestId("new-project-button"));

    expect(screen.getByTestId("new-project-modal")).toBeTruthy();
  });

  it("creating a project via modal updates the active project in store", async () => {
    renderSwitcher();
    await userEvent.click(screen.getByTestId("project-switcher-trigger"));
    await waitFor(() => screen.getByTestId("new-project-button"));
    await userEvent.click(screen.getByTestId("new-project-button"));

    const input = screen.getByLabelText("Project name");
    await userEvent.type(input, "Gamma Project");
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      const state = useProjectStore.getState();
      expect(state.activeProjectId).toBe("proj-3");
      expect(state.activeProjectName).toBe("Gamma Project");
    });
  });

  it("export button triggers download for active project", async () => {
    // Set up an active project and mock the export endpoint
    useProjectStore.setState({
      activeProjectId: "proj-1",
      activeProjectName: "Alpha Project",
    });
    server.use(
      http.get(`${BASE}/projects/proj-1/export`, () =>
        HttpResponse.json({ nodes: [], edges: [] })
      )
    );

    // jsdom does not implement URL.createObjectURL — assign it manually
    URL.createObjectURL = vi.fn().mockReturnValue("blob:test-url");
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    renderSwitcher();
    fireEvent.click(screen.getByTestId("export-button"));

    await waitFor(() => {
      expect(URL.createObjectURL).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
    });

    clickSpy.mockRestore();
  });

  it("shows error state with retry button when GET /projects fails", async () => {
    server.use(
      http.get(`${BASE}/projects`, () =>
        HttpResponse.json({ detail: "DB error" }, { status: 500 })
      )
    );

    renderSwitcher();
    await userEvent.click(screen.getByTestId("project-switcher-trigger"));

    await waitFor(() =>
      expect(screen.getByText("Failed to load projects")).toBeTruthy()
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
  });
});
