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
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AgentScreen } from "../AgentScreen";
import { useProjectStore } from "../../stores/projectStore";
import { apiClient } from "../../api/client";
import type { SseEvent, SseNodeEvent, SseDoneEvent, SseErrorEvent } from "../../types";

// ── Mock streamResearch so we control when events fire ───────────────────────

type StreamCallbacks = {
  onEvent: (e: SseEvent) => void;
  onDone: () => void;
  onError: (e: Error) => void;
};

let capturedCallbacks: StreamCallbacks | null = null;
let capturedAbort: ReturnType<typeof vi.fn>;

vi.mock("../../api/agent", () => ({
  streamResearch: vi.fn(
    (
      _goal: string,
      _depth: string,
      onEvent: (e: SseEvent) => void,
      onDone: () => void,
      onError: (e: Error) => void
    ) => {
      capturedCallbacks = { onEvent, onDone, onError };
      capturedAbort = vi.fn();
      return capturedAbort;
    }
  ),
}));

// ── Constants ─────────────────────────────────────────────────────────────────

const BASE = "http://localhost:8000";
apiClient.defaults.baseURL = BASE;

const PROJECT_ID = "proj-1";

const NODE_EVENTS: SseNodeEvent[] = [
  { event: "node", node: "planner", status: "done" },
  { event: "node", node: "searcher", status: "done" },
  { event: "node", node: "scraper", status: "done" },
  { event: "node", node: "synthesiser", status: "done" },
];

const DONE_EVENT: SseDoneEvent = {
  event: "done",
  report: "## Research Results\n\nFindings here.",
  artifact_id: "art-research-1",
};

const ERROR_EVENT: SseErrorEvent = {
  event: "error",
  detail: "Agent failed to complete",
};

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.post(`${BASE}/projects/${PROJECT_ID}/link`, () =>
    HttpResponse.json({}, { status: 200 })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  capturedCallbacks = null;
});
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderScreen() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AgentScreen />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

async function submitGoal(goal = "Tell me about quantum computing") {
  const textarea = screen.getByTestId("goal-textarea");
  await userEvent.type(textarea, goal);
  const button = screen.getByTestId("run-button");
  await userEvent.click(button);
}

// ── Reset Zustand state ───────────────────────────────────────────────────────

beforeEach(() => {
  useProjectStore.setState({
    activeProjectId: null,
    activeProjectName: null,
  });
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AgentScreen", () => {
  it("renders goal form with textarea and run button", () => {
    renderScreen();
    expect(screen.getByTestId("goal-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("run-button")).toBeInTheDocument();
  });

  it("run button is disabled when goal textarea is empty", () => {
    renderScreen();
    expect(screen.getByTestId("run-button")).toBeDisabled();
  });

  it("progress events render in order after SSE node events", async () => {
    renderScreen();
    await submitGoal();

    // Fire all 4 node events
    act(() => {
      for (const ev of NODE_EVENTS) {
        capturedCallbacks!.onEvent(ev);
      }
    });

    await waitFor(() => {
      expect(screen.getByTestId("progress-row-planner")).toBeInTheDocument();
      expect(screen.getByTestId("progress-row-searcher")).toBeInTheDocument();
      expect(screen.getByTestId("progress-row-scraper")).toBeInTheDocument();
      expect(screen.getByTestId("progress-row-synthesiser")).toBeInTheDocument();
    });
  });

  it("report renders as markdown after done event", async () => {
    renderScreen();
    await submitGoal();

    act(() => {
      capturedCallbacks!.onEvent(DONE_EVENT);
      capturedCallbacks!.onDone();
    });

    // The markdown contains "## Research Results" which renders as <h2>
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
    });
  });

  it("view in map link is present after done event", async () => {
    renderScreen();
    await submitGoal();

    act(() => {
      capturedCallbacks!.onEvent(DONE_EVENT);
      capturedCallbacks!.onDone();
    });

    await waitFor(() => {
      const link = screen.getByTestId("view-in-map-link");
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/map");
    });
  });

  it("error banner shown on SSE error event", async () => {
    renderScreen();
    await submitGoal();

    act(() => {
      capturedCallbacks!.onError(new Error(ERROR_EVENT.detail));
    });

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument();
      expect(
        screen.getByText("Agent failed to complete")
      ).toBeInTheDocument();
    });
  });

  it("abort is called when the component unmounts", async () => {
    const { unmount } = renderScreen();
    await submitGoal();

    unmount();
    expect(capturedAbort).toHaveBeenCalledTimes(1);
  });

  it("links artifact to active project after done event", async () => {
    useProjectStore.setState({
      activeProjectId: PROJECT_ID,
      activeProjectName: "Test Project",
    });

    const linkRequests: string[] = [];
    server.use(
      http.post(`${BASE}/projects/${PROJECT_ID}/link`, async ({ request }) => {
        const body = await request.json() as { node_id: string };
        linkRequests.push(body.node_id);
        return HttpResponse.json({}, { status: 200 });
      })
    );

    renderScreen();
    await submitGoal();

    act(() => {
      capturedCallbacks!.onEvent(DONE_EVENT);
      capturedCallbacks!.onDone();
    });

    await waitFor(() => {
      expect(linkRequests).toContain(DONE_EVENT.artifact_id);
    });
  });
});
