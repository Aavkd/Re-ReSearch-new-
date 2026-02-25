import { describe, it, vi, expect, afterEach } from "vitest";
import { streamResearch } from "../agent";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const encoder = new TextEncoder();

/** Build a ReadableStream that emits the given SSE chunks as Uint8Array. */
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

/** Wrap a stream in a minimal Response-like object. */
function fakeResponse(stream: ReadableStream<Uint8Array>): Response {
  return {
    ok: true,
    status: 200,
    body: stream,
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

afterEach(() => {
  vi.restoreAllMocks();
});

describe("streamResearch", () => {
  it("calls onEvent for each data line including the done event", async () => {
    const chunks = [
      'data: {"event":"node","node":"planner","status":"started"}\n\n',
      'data: {"event":"node","node":"searcher","status":"started"}\n\n',
      'data: {"event":"done","report":"# Report","artifact_id":"art-1"}\n\n',
    ];

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      fakeResponse(makeStream(chunks))
    );

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    // streamResearch runs async internally; we need to wait for it to finish
    await new Promise<void>((resolve) => {
      const wrappedDone = () => {
        onDone();
        resolve();
      };
      streamResearch("test goal", "quick", onEvent, wrappedDone, onError);
    });

    expect(onEvent).toHaveBeenCalledTimes(3);
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onDone exactly once when the done event is received", async () => {
    const chunks = [
      'data: {"event":"done","report":"Final report","artifact_id":"art-99"}\n\n',
    ];

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      fakeResponse(makeStream(chunks))
    );

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await new Promise<void>((resolve) => {
      streamResearch("goal", "standard", onEvent, () => {
        onDone();
        resolve();
      }, onError);
    });

    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it("stops calling callbacks after abort", async () => {
    // Create a stream that only resolves after the test aborts it
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        streamController = controller;
      },
    });

    // fetch resolves immediately with an open stream
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(fakeResponse(stream));

    const onEvent = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    const abort = streamResearch("goal", "deep", onEvent, onDone, onError);

    // Give the async IIFE a chance to start reading
    await new Promise((r) => setTimeout(r, 0));

    // Abort before the stream produces data
    abort();

    // Enqueue data AFTER abort — these should not reach callbacks
    streamController.enqueue(
      encoder.encode(
        'data: {"event":"node","node":"planner","status":"started"}\n\n'
      )
    );
    streamController.close();

    // Wait a tick to let any pending async work drain
    await new Promise((r) => setTimeout(r, 10));

    expect(onEvent).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
