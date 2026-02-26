import { apiClient } from "./client";
import type {
  ChatConversation,
  ChatSseEvent,
  ChatCitationEvent,
  ChatErrorEvent,
} from "../types";

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------

/** Return all conversations for a project. */
export async function listConversations(
  projectId: string
): Promise<ChatConversation[]> {
  const res = await apiClient.get<ChatConversation[]>(
    `/projects/${projectId}/chat`
  );
  return res.data;
}

/** Create a new (empty) conversation. */
export async function createConversation(
  projectId: string,
  title = "New conversation"
): Promise<ChatConversation> {
  const res = await apiClient.post<ChatConversation>(
    `/projects/${projectId}/chat`,
    { title }
  );
  return res.data;
}

/** Fetch a single conversation with its full message history. */
export async function getConversation(
  projectId: string,
  convId: string
): Promise<ChatConversation> {
  const res = await apiClient.get<ChatConversation>(
    `/projects/${projectId}/chat/${convId}`
  );
  return res.data;
}

/** Delete a conversation permanently. */
export async function deleteConversation(
  projectId: string,
  convId: string
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/chat/${convId}`);
}

// ---------------------------------------------------------------------------
// SSE streaming helper
// ---------------------------------------------------------------------------

/**
 * Send a chat message and stream the assistant's reply via Server-Sent Events.
 *
 * The backend endpoint is a POST so we can't use the browser's native
 * `EventSource` API. Instead we open a `fetch` stream and read it as a
 * `ReadableStream`, exactly as `api/agent.ts` does for research runs.
 *
 * @param projectId  Project UUID.
 * @param convId     Conversation UUID.
 * @param message    The user's message text.
 * @param history    Prior `{role, content}` turns sent by the client.
 * @param onEvent    Called for each parsed SSE event (token, citation, done, error).
 * @param onDone     Called exactly once after the `"done"` event.
 * @param onError    Called on `"error"` event or on network/parse failure.
 * @returns          An abort function — call it in `useEffect` cleanup.
 */
export function streamChatMessage(
  projectId: string,
  convId: string,
  message: string,
  history: Array<{ role: string; content: string }>,
  onEvent: (e: ChatSseEvent) => void,
  onDone: () => void,
  onError: (e: Error) => void
): () => void {
  const controller = new AbortController();
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) ?? "";

  (async () => {
    let response: Response;
    try {
      response = await fetch(
        `${baseUrl}/projects/${projectId}/chat/${convId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ message, history }),
          signal: controller.signal,
        }
      );
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
        // Exit immediately if the caller aborted — even if the read returned data.
        if (done || controller.signal.aborted) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines (\n\n).
        const parts = buffer.split("\n\n");
        // The last element may be an incomplete chunk — keep it in the buffer.
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const dataLine = part
            .split("\n")
            .find((line) => line.startsWith("data:"));
          if (!dataLine) continue;

          const jsonStr = dataLine.slice("data:".length).trim();
          let parsed: ChatSseEvent;
          try {
            parsed = JSON.parse(jsonStr) as ChatSseEvent;
          } catch {
            // Malformed event — skip.
            continue;
          }

          onEvent(parsed);

          if (parsed.event === "done") {
            onDone();
            return;
          } else if (parsed.event === "error") {
            onError(new Error((parsed as ChatErrorEvent).detail));
            return;
          }
          // token and citation events fall through — the caller handles them.
          void (parsed as ChatCitationEvent); // keep type-checker happy
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
