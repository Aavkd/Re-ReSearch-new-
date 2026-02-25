import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useProjectList, useCreateProject } from "../../hooks/useProjects";
import type { AppNode } from "../../types";
import React from "react";
import { apiClient } from "../../api/client";

// ── MSW server ──────────────────────────────────────────

const BASE = "http://localhost:8000";

// Point the shared axios instance at the MSW intercepted base URL
apiClient.defaults.baseURL = BASE;

const mockProject: AppNode = {
  id: "node-1",
  node_type: "Project",
  title: "Test Project",
  content_path: null,
  metadata: {},
  created_at: 1700000000,
  updated_at: 1700000000,
};

const server = setupServer(
  http.get(`${BASE}/projects`, () => HttpResponse.json([mockProject])),
  http.post(`${BASE}/projects`, () => HttpResponse.json(mockProject, { status: 201 }))
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helper ───────────────────────────────────────────────

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// ── Tests ────────────────────────────────────────────────

describe("useProjectList", () => {
  it("fetches projects on mount and returns array", async () => {
    const { result } = renderHook(() => useProjectList(), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockProject]);
  });
});

describe("useCreateProject", () => {
  it("calls POST /projects and invalidates the projects list", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateProject(), { wrapper });
    result.current.mutate("New Project");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["projects"] })
    );
  });
});
