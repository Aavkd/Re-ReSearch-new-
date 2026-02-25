import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";

/**
 * Two-column application shell.
 *
 * ┌──────────────────────────────────────────────────────┐
 * │  Sidebar (fixed, w-64)  │  Main content (flex fill)  │
 * │  ProjectSwitcher        │  <Outlet />                │
 * │  NavBar                 │                            │
 * └──────────────────────────────────────────────────────┘
 *
 * The sidebar and main content area each scroll independently.
 * ProjectSwitcher is imported lazily here as a placeholder comment so the
 * slot is clearly visible; it will be swapped for the real component in F4.
 */
export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* ── Sidebar ───────────────────────────────────────── */}
      <aside className="flex w-64 flex-shrink-0 flex-col overflow-y-auto border-r border-gray-200 bg-white">
        {/* Project switcher slot — implemented in Phase F4 */}
        <div
          className="border-b border-gray-200 px-4 py-3 text-xs text-gray-400"
          data-testid="project-switcher-slot"
        >
          {/* <ProjectSwitcher /> */}
          Project switcher (F4)
        </div>

        {/* Navigation */}
        <div className="mt-2 flex-1">
          <NavBar />
        </div>
      </aside>

      {/* ── Main content area ─────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
