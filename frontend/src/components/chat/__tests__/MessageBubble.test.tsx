import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { act } from "react";
import { MessageBubble } from "../MessageBubble";
import { useChatStore } from "../../../stores/chatStore";
import type { ChatMessage } from "../../../types";

const USER_MSG: ChatMessage = {
  role: "user",
  content: "Hello there",
  ts: 1700000000,
};

const ASSISTANT_MSG: ChatMessage = {
  role: "assistant",
  content: "**Bold** and _italic_ reply",
  ts: 1700000001,
};

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  act(() => {
    useChatStore.setState({ streamingContent: "", isStreaming: false });
  });
});

describe("MessageBubble", () => {
  it("renders user message right-aligned", () => {
    wrap(<MessageBubble message={USER_MSG} />);
    const bubble = screen.getByTestId("user-bubble");
    expect(bubble).toHaveClass("justify-end");
    // Should contain the plain text
    expect(screen.getByText("Hello there")).toBeTruthy();
  });

  it("renders assistant markdown — bold is <strong>", () => {
    wrap(<MessageBubble message={ASSISTANT_MSG} />);
    expect(screen.getByTestId("assistant-bubble")).toBeTruthy();
    // react-markdown renders **text** as <strong>
    expect(screen.getByRole("strong") ?? document.querySelector("strong")).toBeTruthy();
  });

  it("streaming bubble appends cursor character when isStreaming=true", () => {
    act(() => {
      useChatStore.setState({ streamingContent: "Hello" });
    });
    wrap(
      <MessageBubble
        message={{ role: "assistant", content: "", ts: 1700000002 }}
        isStreaming={true}
      />
    );
    // The rendered content should contain the blinking cursor ▍
    const container = screen.getByTestId("assistant-bubble");
    expect(container.textContent).toContain("▍");
  });

  it("non-streaming assistant bubble shows message.content not streamingContent", () => {
    act(() => {
      useChatStore.setState({ streamingContent: "SHOULD NOT APPEAR" });
    });
    wrap(<MessageBubble message={ASSISTANT_MSG} />);
    // The rendered markdown text should come from message.content, not the store
    expect(screen.queryByText(/SHOULD NOT APPEAR/)).toBeNull();
  });
});
