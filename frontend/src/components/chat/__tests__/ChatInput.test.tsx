import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "../ChatInput";

function wrap(onSend = vi.fn(), disabled = false) {
  return render(<ChatInput onSend={onSend} disabled={disabled} />);
}

describe("ChatInput", () => {
  it("send button is disabled when input is empty", () => {
    wrap();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("send button is disabled when disabled prop is true", async () => {
    const user = userEvent.setup();
    wrap(vi.fn(), true);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Hello");
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("Enter key calls onSend with the input value", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    wrap(onSend);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "My question");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledOnce();
    expect(onSend).toHaveBeenCalledWith("My question");
  });

  it("Shift+Enter inserts newline and does NOT call onSend", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    wrap(onSend);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "line1");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("input clears after send via Enter", async () => {
    const user = userEvent.setup();
    wrap();
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "Hello");
    await user.keyboard("{Enter}");
    expect(textarea.value).toBe("");
  });

  it("input clears after clicking send button", async () => {
    const user = userEvent.setup();
    wrap();
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(textarea, "Hello again");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(textarea.value).toBe("");
  });
});
