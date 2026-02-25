import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
import { ProjectSwitcher } from "../sidebar/ProjectSwitcher";

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
 */
export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* ── Sidebar ───────────────────────────────────────── */}
      <aside className="flex w-64 flex-shrink-0 flex-col overflow-y-auto border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        {/* Project switcher — implemented in Phase F4 */}
        <div
          className="border-b border-gray-200 dark:border-gray-800"
          data-testid="project-switcher-slot"
        >
          <ProjectSwitcher />
        </div>

        {/* Navigation */}
        <div className="mt-2 flex flex-1 flex-col">
          <NavBar />
        </div>
      </aside>

      {/* ── Main content area ─────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-y-auto bg-white dark:bg-gray-950">
        <Outlet />
      </main>
    </div>
  );
}
