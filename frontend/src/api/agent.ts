import type { ResearchDepth, SseEvent, SseNodeEvent, SseDoneEvent, SseErrorEvent } from "../types";

/**
 * Stream a research run from `POST /research` over Server-Sent Events.
 *
 * The `/research` endpoint is a POST, so we cannot use the browser's native
 * `EventSource` API (which only supports GET).  Instead we use `fetch` with
 * `Accept: text/event-stream` and read the body as a `ReadableStream`.
 *
 * @param goal       The research goal text.
 * @param depth      Research depth: "quick" | "standard" | "deep".
 * @param onEvent    Called for each `node` SSE event during the run.
 * @param onDone     Called once when the `done` event is received.
 * @param onError    Called if an `error` event or a network error occurs.
 * @returns          An abort function — call it in `useEffect` cleanup.
 */
export function streamResearch(
  goal: string,
  depth: ResearchDepth,
  onEvent: (e: SseEvent) => void,
  onDone: () => void,
  onError: (e: Error) => void
): () => void {
  const controller = new AbortController();
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) ?? "";

  (async () => {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ goal, depth }),
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
      return;
    }

    if (!response.ok) {
      onError(new Error(`Request failed with status ${response.status}`));
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError(new Error("Response body is not readable"));
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        // Exit immediately if the caller aborted — even if the read returned data
        if (done || controller.signal.aborted) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines (\n\n)
        const parts = buffer.split("\n\n");
        // The last element may be an incomplete chunk — keep it in the buffer
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const dataLine = part
            .split("\n")
            .find((line) => line.startsWith("data:"));
          if (!dataLine) continue;

          const jsonStr = dataLine.slice("data:".length).trim();
          let parsed: SseEvent;
          try {
            parsed = JSON.parse(jsonStr) as SseEvent;
          } catch {
            // Malformed event — skip
            continue;
          }

          if (parsed.event === "done") {
            onEvent(parsed);
            onDone();
            return;
          } else if (parsed.event === "error") {
            onEvent(parsed);
            onError(new Error((parsed as SseErrorEvent).detail));
            return;
          } else {
            // node event
            onEvent(parsed as SseNodeEvent | SseDoneEvent);
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      reader.releaseLock();
    }
  })();

  return () => controller.abort();
}
