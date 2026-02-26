import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ChatScreen } from "../ChatScreen";
import { useProjectStore } from "../../stores/projectStore";
import { useChatStore } from "../../stores/chatStore";
import type { ChatConversation, ChatSseEvent, ChatCitationEvent } from "../../types";

// ── Mock api/chat ─────────────────────────────────────────────────────────────
// vi.mock is hoisted, so the factory must NOT reference variables defined below.
// Use vi.fn() placeholders and configure return values in beforeEach.

type StreamCallbacks = {
  onEvent: (e: ChatSseEvent) => void;
  onDone: () => void;
  onError: (e: Error) => void;
};

let capturedCallbacks: StreamCallbacks | null = null;
const mockAbort = vi.fn();

vi.mock("../../api/chat", () => ({
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
  streamChatMessage: vi.fn(
    (
      _projectId: string,
      _convId: string,
      _message: string,
      _history: unknown[],
      onEvent: (e: ChatSseEvent) => void,
      onDone: () => void,
      onError: (e: Error) => void
    ) => {
      capturedCallbacks = { onEvent, onDone, onError };
      return mockAbort;
    }
  ),
}));

// Import after vi.mock so we can configure return values via vi.mocked().
import * as chatApi from "../../api/chat";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function CONV_FIXTURE(override: Partial<ChatConversation> = {}): ChatConversation {
  return {
    id: "conv-1",
    title: "Test conversation",
    messages: [
      { role: "user", content: "Hello", ts: 1700000001 },
      { role: "assistant", content: "Hi there!", ts: 1700000002 },
    ],
    created_at: 1700000000,
    updated_at: 1700000002,
    ...override,
  };
}

const PROJECT_ID = "proj-test";
const CONV_ID = "conv-1";

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderScreen() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChatScreen />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ── Setup / teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  capturedCallbacks = null;
  mockAbort.mockClear();

  // Configure mock return values (cannot be done in the hoisted factory)
  vi.mocked(chatApi.listConversations).mockResolvedValue([CONV_FIXTURE()]);
  vi.mocked(chatApi.createConversation).mockResolvedValue(CONV_FIXTURE());
  vi.mocked(chatApi.getConversation).mockResolvedValue(CONV_FIXTURE());
  vi.mocked(chatApi.deleteConversation).mockResolvedValue(undefined);

  useProjectStore.setState({ activeProjectId: null, activeProjectName: null });
  act(() => {
    useChatStore.setState({
      activeConvId: null,
      localMessages: [],
      isStreaming: false,
      streamingContent: "",
      citations: [],
    });
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("ChatScreen", () => {
  it("shows empty state when no project selected", () => {
    renderScreen();
    expect(screen.getByText(/select a project/i)).toBeInTheDocument();
  });

  it("shows empty state when project selected but no conv selected", () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    renderScreen();
    expect(screen.getByText(/select or create a conversation/i)).toBeInTheDocument();
  });

  it("message list renders user and assistant bubbles from server", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("user-bubble").length).toBeGreaterThan(0);
      expect(screen.getAllByTestId("assistant-bubble").length).toBeGreaterThan(0);
    });
  });

  it("sending a message appends a user bubble optimistically", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });
    const user = userEvent.setup();

    renderScreen();

    // Wait for conversation to load
    await waitFor(() => screen.getAllByTestId("user-bubble"));

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "New question");
    await user.keyboard("{Enter}");

    // An extra user bubble should appear immediately (optimistic)
    await waitFor(() => {
      const bubbles = screen.getAllByTestId("user-bubble");
      const texts = bubbles.map((b) => b.textContent);
      expect(texts.some((t) => t?.includes("New question"))).toBe(true);
    });
  });

  it("streaming tokens update the streaming bubble", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });
    const user = userEvent.setup();

    renderScreen();
    await waitFor(() => screen.getAllByTestId("user-bubble"));

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Stream me");
    await user.keyboard("{Enter}");

    // Fire token events
    act(() => {
      capturedCallbacks!.onEvent({ event: "token", text: "Partial " });
      capturedCallbacks!.onEvent({ event: "token", text: "answer." });
    });

    await waitFor(() => {
      expect(useChatStore.getState().streamingContent).toBe("Partial answer.");
    });
  });

  it("done event finalises the assistant bubble", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });
    const user = userEvent.setup();

    renderScreen();
    await waitFor(() => screen.getAllByTestId("user-bubble"));

    await user.type(screen.getByRole("textbox"), "Question");
    await user.keyboard("{Enter}");

    act(() => {
      capturedCallbacks!.onEvent({ event: "token", text: "Full reply." });
      capturedCallbacks!.onDone();
    });

    await waitFor(() => {
      expect(useChatStore.getState().isStreaming).toBe(false);
      expect(useChatStore.getState().streamingContent).toBe("");
    });
    // The assistant bubble should contain the reply text in localMessages
    const localMsgs = useChatStore.getState().localMessages;
    expect(localMsgs.some((m) => m.role === "assistant" && m.content === "Full reply.")).toBe(true);
  });

  it("citations panel appears after done event", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });
    const user = userEvent.setup();

    renderScreen();
    await waitFor(() => screen.getAllByTestId("user-bubble"));

    await user.type(screen.getByRole("textbox"), "Cite me");
    await user.keyboard("{Enter}");

    act(() => {
      capturedCallbacks!.onEvent({
        event: "citation",
        nodes: [{ id: "node-1", title: "Source One" }],
      } as ChatCitationEvent);
      capturedCallbacks!.onDone();
    });

    await waitFor(() => {
      expect(useChatStore.getState().citations).toHaveLength(1);
    });

    // After streaming is done, citation list should appear in the DOM
    await waitFor(() => {
      expect(screen.getByTestId("citation-list")).toBeInTheDocument();
      expect(screen.getByText("Source One")).toBeInTheDocument();
    });
  });

  it("abort is called on unmount while streaming", async () => {
    useProjectStore.setState({ activeProjectId: PROJECT_ID, activeProjectName: "P" });
    act(() => { useChatStore.setState({ activeConvId: CONV_ID }); });
    const user = userEvent.setup();

    const { unmount } = renderScreen();
    await waitFor(() => screen.getAllByTestId("user-bubble"));

    await user.type(screen.getByRole("textbox"), "Unmount test");
    await user.keyboard("{Enter}");

    // Streaming is in progress (onDone not called)
    expect(capturedCallbacks).not.toBeNull();

    unmount();
    expect(mockAbort).toHaveBeenCalledTimes(1);
  });
});
