import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { apiClient } from "../client";
import {
  fetchProjects,
  createProject,
  linkNodeToProject,
} from "../projects";
import type { AppNode } from "../../types";

const BASE = "http://localhost:8000";

apiClient.defaults.baseURL = BASE;

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const PROJECT_NODE: AppNode = {
  id: "proj-1",
  node_type: "Project",
  title: "My Project",
  content_path: null,
  metadata: {},
  created_at: 1700000000,
  updated_at: 1700000000,
};

describe("fetchProjects", () => {
  it("returns an array of AppNode", async () => {
    server.use(
      http.get(`${BASE}/projects`, () =>
        HttpResponse.json([PROJECT_NODE], { status: 200 })
      )
    );

    const projects = await fetchProjects();
    expect(projects).toHaveLength(1);
    expect(projects[0].id).toBe("proj-1");
    expect(projects[0].node_type).toBe("Project");
  });

  it("returns an empty array for empty list", async () => {
    server.use(
      http.get(`${BASE}/projects`, () => HttpResponse.json([], { status: 200 }))
    );

    const projects = await fetchProjects();
    expect(projects).toEqual([]);
  });
});

describe("createProject", () => {
  it("POSTs the correct body { name }", async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${BASE}/projects`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ ...PROJECT_NODE, title: "Test" }, { status: 201 });
      })
    );

    const node = await createProject("Test");
    expect(capturedBody).toEqual({ name: "Test" });
    expect(node.title).toBe("Test");
  });
});

describe("linkNodeToProject", () => {
  it("POSTs { node_id, relation } to /projects/{id}/link", async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${BASE}/projects/proj-1/link`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          { project_id: "proj-1", node_id: "node-2", relation: "HAS_ARTIFACT" },
          { status: 201 }
        );
      })
    );

    await linkNodeToProject("proj-1", "node-2", "HAS_ARTIFACT");
    expect(capturedBody).toEqual({ node_id: "node-2", relation: "HAS_ARTIFACT" });
  });

  it("uses HAS_SOURCE as the default relation", async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${BASE}/projects/proj-1/link`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          { project_id: "proj-1", node_id: "node-3", relation: "HAS_SOURCE" },
          { status: 201 }
        );
      })
    );

    await linkNodeToProject("proj-1", "node-3");
    expect(capturedBody).toEqual({ node_id: "node-3", relation: "HAS_SOURCE" });
  });
});
