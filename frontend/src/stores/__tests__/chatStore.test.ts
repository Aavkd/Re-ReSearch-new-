import { beforeEach, describe, expect, it } from "vitest";
import { act } from "react";
import { useChatStore } from "../../stores/chatStore";
import type { ChatMessage } from "../../types";

// Reset the store and clear sessionStorage before every test
beforeEach(() => {
  sessionStorage.clear();
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

describe("useChatStore", () => {
  it("initial streaming state is false", () => {
    const state = useChatStore.getState();
    expect(state.isStreaming).toBe(false);
  });

  it("setIsStreaming toggles the flag", () => {
    act(() => {
      useChatStore.getState().setIsStreaming(true);
    });
    expect(useChatStore.getState().isStreaming).toBe(true);

    act(() => {
      useChatStore.getState().setIsStreaming(false);
    });
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it("appendStreamingContent accumulates text", () => {
    act(() => {
      useChatStore.getState().appendStreamingContent("Hello");
    });
    act(() => {
      useChatStore.getState().appendStreamingContent(", world");
    });
    expect(useChatStore.getState().streamingContent).toBe("Hello, world");
  });

  it("resetStreamingContent clears to empty string", () => {
    act(() => {
      useChatStore.getState().appendStreamingContent("some text");
    });
    act(() => {
      useChatStore.getState().resetStreamingContent();
    });
    expect(useChatStore.getState().streamingContent).toBe("");
  });

  it("addLocalMessage appends to array", () => {
    const msg: ChatMessage = { role: "user", content: "Hi", ts: 1700000000 };
    act(() => {
      useChatStore.getState().addLocalMessage(msg);
    });
    expect(useChatStore.getState().localMessages).toHaveLength(1);
    expect(useChatStore.getState().localMessages[0]).toEqual(msg);
  });

  it("addLocalMessage preserves insertion order", () => {
    const msg1: ChatMessage = { role: "user", content: "First", ts: 1700000001 };
    const msg2: ChatMessage = { role: "assistant", content: "Second", ts: 1700000002 };
    act(() => {
      useChatStore.getState().addLocalMessage(msg1);
      useChatStore.getState().addLocalMessage(msg2);
    });
    const { localMessages } = useChatStore.getState();
    expect(localMessages).toHaveLength(2);
    expect(localMessages[0].content).toBe("First");
    expect(localMessages[1].content).toBe("Second");
  });

  it("clearLocalMessages empties array", () => {
    act(() => {
      useChatStore.getState().addLocalMessage({ role: "user", content: "msg", ts: 1 });
      useChatStore.getState().addLocalMessage({ role: "assistant", content: "reply", ts: 2 });
    });
    expect(useChatStore.getState().localMessages).toHaveLength(2);

    act(() => {
      useChatStore.getState().clearLocalMessages();
    });
    expect(useChatStore.getState().localMessages).toHaveLength(0);
  });

  it("setActiveConv updates activeConvId", () => {
    act(() => {
      useChatStore.getState().setActiveConv("conv-123");
    });
    expect(useChatStore.getState().activeConvId).toBe("conv-123");
  });

  it("setActiveConv accepts null to deselect", () => {
    act(() => {
      useChatStore.getState().setActiveConv("conv-123");
    });
    act(() => {
      useChatStore.getState().setActiveConv(null);
    });
    expect(useChatStore.getState().activeConvId).toBeNull();
  });

  it("setCitations replaces the citations array", () => {
    const cites = [{ id: "n1", title: "Source A", url: "https://example.com" }];
    act(() => {
      useChatStore.getState().setCitations(cites);
    });
    expect(useChatStore.getState().citations).toEqual(cites);
  });
});
