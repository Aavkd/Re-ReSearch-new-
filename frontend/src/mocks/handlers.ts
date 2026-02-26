/**
 * MSW default request handlers.
 *
 * These handlers provide realistic stub responses for every backend route.
 * Individual tests override them via `server.use(...)` for edge-case scenarios.
 */
import { http, HttpResponse } from "msw";

const BASE = "http://localhost:8000";

// ── Fixture data ──────────────────────────────────────────────────────────────

const PROJECT = {
  id: "proj-default",
  node_type: "Project",
  title: "Default Project",
  content_path: null,
  metadata: {},
  created_at: 1700000000,
  updated_at: 1700000000,
};

const SOURCE_NODE = {
  id: "node-src-default",
  node_type: "Source",
  title: "Example Source",
  content_path: null,
  metadata: { url: "https://example.com" },
  created_at: 1700000000,
  updated_at: 1700000000,
};

const ARTIFACT_NODE = {
  id: "node-art-default",
  node_type: "Artifact",
  title: "Example Artifact",
  content_path: null,
  metadata: { content_body: "" },
  created_at: 1700000001,
  updated_at: 1700000001,
};

const CONVERSATION = {
  id: "conv-default",
  title: "Default Conversation",
  messages: [
    { role: "user",      content: "Hello",       ts: 1700000010 },
    { role: "assistant", content: "Hi there!",   ts: 1700000011 },
  ],
  created_at: 1700000010,
  updated_at: 1700000011,
};

// ── Handlers ──────────────────────────────────────────────────────────────────

export const handlers = [
  // Projects
  http.get(`${BASE}/projects`, () => HttpResponse.json([PROJECT])),
  http.post(`${BASE}/projects`, async ({ request }) => {
    const body = await request.json() as { name: string };
    return HttpResponse.json(
      { ...PROJECT, id: "proj-new", title: body.name },
      { status: 201 }
    );
  }),
  http.get(`${BASE}/projects/:id`, ({ params }) =>
    HttpResponse.json({
      project_id: params.id,
      by_type: { Source: 1, Artifact: 1 },
      recent_artifacts: ["Example Artifact"],
    })
  ),
  http.get(`${BASE}/projects/:id/nodes`, () =>
    HttpResponse.json([SOURCE_NODE, ARTIFACT_NODE])
  ),
  http.get(`${BASE}/projects/:id/graph`, () =>
    HttpResponse.json({ nodes: [SOURCE_NODE, ARTIFACT_NODE], edges: [] })
  ),
  http.post(`${BASE}/projects/:id/link`, () =>
    HttpResponse.json({}, { status: 200 })
  ),
  http.get(`${BASE}/projects/:id/export`, () =>
    HttpResponse.json({ nodes: [SOURCE_NODE, ARTIFACT_NODE], edges: [] })
  ),

  // Ingest
  http.post(`${BASE}/ingest/url`, () =>
    HttpResponse.json({
      node_id: "node-ingested",
      title: "Ingested Article",
      node_type: "Source",
      metadata: {},
    })
  ),
  http.post(`${BASE}/ingest/pdf`, () =>
    HttpResponse.json({
      node_id: "node-pdf",
      title: "Ingested PDF",
      node_type: "Source",
      metadata: {},
    })
  ),

  // Search
  http.get(`${BASE}/search`, () =>
    HttpResponse.json([SOURCE_NODE, ARTIFACT_NODE])
  ),

  // Nodes
  http.get(`${BASE}/nodes`, ({ request }) => {
    const url = new URL(request.url);
    const type = url.searchParams.get("type");
    if (type === "Artifact") return HttpResponse.json([ARTIFACT_NODE]);
    if (type === "Source") return HttpResponse.json([SOURCE_NODE]);
    return HttpResponse.json([SOURCE_NODE, ARTIFACT_NODE]);
  }),
  http.post(`${BASE}/nodes`, async ({ request }) => {
    const body = await request.json() as Partial<typeof SOURCE_NODE>;
    return HttpResponse.json(
      { ...ARTIFACT_NODE, id: "node-created", title: body.title ?? "New Node" },
      { status: 201 }
    );
  }),
  http.get(`${BASE}/nodes/:id`, ({ params }) =>
    HttpResponse.json({ ...ARTIFACT_NODE, id: params.id })
  ),
  http.put(`${BASE}/nodes/:id`, async ({ params, request }) => {
    const body = await request.json() as Partial<typeof ARTIFACT_NODE>;
    return HttpResponse.json({ ...ARTIFACT_NODE, id: params.id, ...body });
  }),
  http.delete(`${BASE}/nodes/:id`, () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Chat — conversation CRUD + SSE message stream
  http.get(`${BASE}/projects/:id/chat`, () =>
    HttpResponse.json([CONVERSATION])
  ),
  http.post(`${BASE}/projects/:id/chat`, async ({ request }) => {
    const body = await request.json() as { title?: string };
    return HttpResponse.json(
      { ...CONVERSATION, id: "conv-new", title: body.title ?? "New conversation", messages: [] },
      { status: 201 }
    );
  }),
  http.get(`${BASE}/projects/:id/chat/:convId`, ({ params }) =>
    HttpResponse.json({ ...CONVERSATION, id: params.convId as string })
  ),
  http.post(`${BASE}/projects/:id/chat/:convId/messages`, () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode('data: {"event":"token","text":"Hello from stub"}\n\n')
        );
        controller.enqueue(
          encoder.encode(
            'data: {"event":"citation","nodes":[{"id":"node-src-default","title":"Example Source","url":"https://example.com"}]}\n\n'
          )
        );
        controller.enqueue(encoder.encode('data: {"event":"done"}\n\n'));
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
  http.delete(`${BASE}/projects/:id/chat/:convId`, () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Research (SSE stream — returns a minimal done event)
  http.post(`${BASE}/research`, () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'data: {"event":"done","report":"## Report","artifact_id":"art-stream"}\n\n'
          )
        );
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
];
