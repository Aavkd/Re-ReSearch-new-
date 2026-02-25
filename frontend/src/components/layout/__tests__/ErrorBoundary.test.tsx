import { describe, expect, it, vi, beforeEach } from "vitest";
import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorBoundary } from "../ErrorBoundary";

// Suppress React's noisy console.error output for expected render errors
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
});

// ── Helper ────────────────────────────────────────────────────────────────────

/** Component that unconditionally throws on render. */
function BombComponent(): ReactElement {
  throw new Error("Intentional render error");
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ErrorBoundary", () => {
  it("catches a render error and shows the fallback UI", () => {
    render(
      <ErrorBoundary>
        <BombComponent />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("displays the error message in the fallback", () => {
    render(
      <ErrorBoundary>
        <BombComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Intentional render error")).toBeInTheDocument();
  });

  it("shows a Reload button in the fallback", () => {
    render(
      <ErrorBoundary>
        <BombComponent />
      </ErrorBoundary>
    );

    const reloadBtn = screen.getByRole("button", { name: /reload/i });
    expect(reloadBtn).toBeInTheDocument();
  });

  it("calls window.location.reload when Reload is clicked", async () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, "location", {
      value: { reload: reloadMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <BombComponent />
      </ErrorBoundary>
    );

    await userEvent.click(screen.getByRole("button", { name: /reload/i }));
    expect(reloadMock).toHaveBeenCalledTimes(1);
  });

  it("renders children normally when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div data-testid="healthy-child">All good</div>
      </ErrorBoundary>
    );

    expect(screen.getByTestId("healthy-child")).toBeInTheDocument();
    expect(
      screen.queryByTestId("error-boundary-fallback")
    ).not.toBeInTheDocument();
  });
});
