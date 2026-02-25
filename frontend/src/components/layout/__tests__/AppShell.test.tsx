import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "../AppShell";
import { LibraryScreen } from "../../../screens/LibraryScreen";

function renderShell(initialEntry = "/library") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route
              index
              element={
                <LibraryScreen />
              }
            />
            <Route path="library" element={<LibraryScreen />} />
            <Route path="map" element={<div>MapScreen placeholder</div>} />
            <Route path="drafts" element={<div>DraftsScreen placeholder</div>} />
            <Route path="agent" element={<div>AgentScreen placeholder</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AppShell", () => {
  it("renders the sidebar with a project-switcher slot", () => {
    renderShell();
    expect(screen.getByTestId("project-switcher-slot")).toBeTruthy();
  });

  it("renders all four nav links", () => {
    renderShell();
    expect(screen.getByRole("link", { name: /library/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /map/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /drafts/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /agent/i })).toBeTruthy();
  });

  it("applies active class to the Library link when at /library", () => {
    renderShell("/library");
    const link = screen.getByRole("link", { name: /library/i });
    expect(link.className).toMatch(/bg-blue-100/);
    expect(link.className).toMatch(/text-blue-800/);
  });

  it("does not apply active class to non-active links", () => {
    renderShell("/library");
    const mapLink = screen.getByRole("link", { name: /map/i });
    expect(mapLink.className).not.toMatch(/bg-blue-100/);
  });

  it("renders the outlet content for the active route", () => {
    renderShell("/library");
    expect(screen.getByTestId("library-screen")).toBeTruthy();
  });
});
