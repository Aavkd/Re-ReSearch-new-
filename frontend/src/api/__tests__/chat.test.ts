import { describe, it, vi, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { apiClient } from "../client";
import {
  listConversations,
  createConversation,
  streamChatMessage,
} from "../chat";
import type { ChatConversation } from "../../types";

const BASE = "http://localhost:8000";

apiClient.defaults.baseURL = BASE;

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const CONV: ChatConversation = {
  id: "conv-1",
  title: "Test conversation",
  messages: [],
  created_at: 1700000000,
  updated_at: 1700000000,
};

// ---------------------------------------------------------------------------
// Streaming helpers (mirrors agent.test.ts)
// ---------------------------------------------------------------------------

const encoder = new TextEncoder();

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const iter = chunks[Symbol.iterator]();
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      const next = iter.next();
      if (next.done) {
        controller.close();
      } else {
        controller.enqueue(encoder.encode(next.value));
      }
    },
  });
}

function fakeResponse(stream: ReadableStream<Uint8Array>): Response {
  return {
    ok: true,
    status: 200,
    body: stream,
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// REST tests
// ---------------------------------------------------------------------------

describe("listConversations", () => {
  it("returns array of ChatConversation", async () => {
    server.use(
      http.get(`${BASE}/projects/proj-1/chat`, () =>
        HttpResponse.json([CONV], { status: 200 })
      )
    );

    const convs = await listConversations("proj-1");
    expect(convs).toHaveLength(1);
    expect(convs[0].id).toBe("conv-1");
    expect(convs[0].title).toBe("Test conversation");
  });
});

describe("createConversation", () => {
  it("POSTs correct body { title }", async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${BASE}/projects/proj-1/chat`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          { ...CONV, title: "My Chat" },
          { status: 201 }
        );
      })
    );

    const conv = await createConversation("proj-1", "My Chat");
    expect(capturedBody).toEqual({ title: "My Chat" });
    expect(conv.title).toBe("My Chat");
  });
});

// ---------------------------------------------------------------------------
// Streaming tests
// ---------------------------------------------------------------------------

describe("streamChatMessage", () => {
  it("dispatches token events via onEvent", async () => {
    const chunks = [
      'data: {"event":"token","text":"Hello"}\n\n',
      'data: {"event":"token","text":" world"}\n\n',
      'data: {"event":"done"}\n\n',
    ];

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      fakeResponse(makeStream(chunks))
    );

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await new Promise<void>((resolve) => {
      streamChatMessage(
        "proj-1",
        "conv-1",
        "Hi",
        [],
        onEvent,
        () => {
          onDone();
          resolve();
        },
        onError
      );
    });

    // Two token events + one done event
    expect(onEvent).toHaveBeenCalledTimes(3);
    expect(onEvent).toHaveBeenNthCalledWith(1, { event: "token", text: "Hello" });
    expect(onEvent).toHaveBeenNthCalledWith(2, { event: "token", text: " world" });
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onDone exactly once after the done event", async () => {
    const chunks = ['data: {"event":"done"}\n\n'];

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      fakeResponse(makeStream(chunks))
    );

    const onDone = vi.fn();
    const onError = vi.fn();

    await new Promise<void>((resolve) => {
      streamChatMessage("proj-1", "conv-1", "Hi", [], vi.fn(), () => {
        onDone();
        resolve();
      }, onError);
    });

    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it("stops dispatching events after abort", async () => {
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        streamController = controller;
      },
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(fakeResponse(stream));

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    const abort = streamChatMessage(
      "proj-1",
      "conv-1",
      "Hi",
      [],
      onEvent,
      onDone,
      onError
    );

    // Give the async IIFE a tick to start reading
    await new Promise((r) => setTimeout(r, 0));

    // Abort before any data arrives
    abort();

    // Enqueue data AFTER abort — must not reach callbacks
    streamController.enqueue(
      encoder.encode('data: {"event":"token","text":"late"}\n\n')
    );
    streamController.close();

    // Drain any pending async work
    await new Promise((r) => setTimeout(r, 10));

    expect(onEvent).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
