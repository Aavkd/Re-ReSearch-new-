import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import React from "react";
import { apiClient } from "../../api/client";
import {
  useConversationList,
  useCreateConversation,
  useDeleteConversation,
} from "../../hooks/useChat";
import { useChatStore } from "../../stores/chatStore";
import type { ChatConversation } from "../../types";

// ── MSW server ──────────────────────────────────────────

const BASE = "http://localhost:8000";
apiClient.defaults.baseURL = BASE;

const PROJECT_ID = "proj-1";
const CONV_ID = "conv-abc";

const mockConv: ChatConversation = {
  id: CONV_ID,
  title: "Test Conversation",
  messages: [],
  created_at: 1700000000,
  updated_at: 1700000000,
};

const server = setupServer(
  http.get(`${BASE}/projects/:projectId/chat`, () =>
    HttpResponse.json([mockConv])
  ),
  http.post(`${BASE}/projects/:projectId/chat`, () =>
    HttpResponse.json(mockConv, { status: 201 })
  ),
  http.delete(`${BASE}/projects/:projectId/chat/:convId`, () =>
    new HttpResponse(null, { status: 204 })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  // Reset chat store between tests
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

// ── useConversationList ───────────────────────────────────

describe("useConversationList", () => {
  it("fetches conversations for a project and returns the array", async () => {
    const { result } = renderHook(() => useConversationList(PROJECT_ID), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockConv]);
  });

  it("is disabled when projectId is null", () => {
    const { result } = renderHook(() => useConversationList(null), {
      wrapper: makeWrapper(),
    });
    // Should never enter loading state when disabled
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });
});

// ── useCreateConversation ─────────────────────────────────

describe("useCreateConversation", () => {
  it("posts to /projects/{id}/chat and returns the new conversation", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateConversation(), { wrapper });
    result.current.mutate({ projectId: PROJECT_ID, title: "My chat" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockConv);
  });

  it("invalidates conversation list on success", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateConversation(), { wrapper });
    result.current.mutate({ projectId: PROJECT_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["conversations", PROJECT_ID] })
    );
  });
});

// ── useDeleteConversation ─────────────────────────────────

describe("useDeleteConversation", () => {
  it("sends DELETE and invalidates conversation list", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteConversation(), { wrapper });
    result.current.mutate({ projectId: PROJECT_ID, convId: CONV_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["conversations", PROJECT_ID] })
    );
  });

  it("clears activeConvId if the deleted conv was active", async () => {
    // Pre-set the active conv
    act(() => {
      useChatStore.getState().setActiveConv(CONV_ID);
    });
    expect(useChatStore.getState().activeConvId).toBe(CONV_ID);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteConversation(), { wrapper });
    result.current.mutate({ projectId: PROJECT_ID, convId: CONV_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(useChatStore.getState().activeConvId).toBeNull();
  });

  it("does NOT clear activeConvId when a different conv is deleted", async () => {
    act(() => {
      useChatStore.getState().setActiveConv("other-conv");
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteConversation(), { wrapper });
    result.current.mutate({ projectId: PROJECT_ID, convId: CONV_ID });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Still "other-conv" — not cleared
    expect(useChatStore.getState().activeConvId).toBe("other-conv");
  });
});
