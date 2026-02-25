import { useState, useRef, useEffect } from "react";
import { useProjectList } from "../../hooks/useProjects";
import { useProjectStore } from "../../stores/projectStore";
import { exportProject } from "../../api/projects";
import { NewProjectModal } from "./NewProjectModal";

/**
 * Sidebar component that shows the active project and allows switching.
 *
 * - Dropdown lists all projects from the `useProjectList` hook.
 * - "+ New Project" button opens `NewProjectModal`.
 * - "↓ Export" button downloads the project graph as JSON.
 * - Loading: skeleton shimmer rows.
 * - Error: "Failed to load projects" with a retry button.
 * - No active project: greyed-out placeholder text.
 */
export function ProjectSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { activeProjectId, activeProjectName, setActiveProject } =
    useProjectStore();

  const { data: projects, isLoading, isError, refetch } = useProjectList();

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [isOpen]);

  const handleExport = async () => {
    if (!activeProjectId) return;
    const data = await exportProject(activeProjectId);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${activeProjectName ?? "project"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative" data-testid="project-switcher" ref={containerRef}>
      {/* ── Trigger row ─────────────────────────────────── */}
      <div className="flex items-center gap-1 p-2">
        <button
          className="flex-1 truncate rounded px-2 py-1.5 text-left text-sm font-medium text-gray-800 hover:bg-gray-100"
          onClick={() => setIsOpen((o) => !o)}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          data-testid="project-switcher-trigger"
        >
          {activeProjectName ?? (
            <span className="text-gray-400">No project selected</span>
          )}
        </button>

        {activeProjectId && (
          <button
            onClick={handleExport}
            className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100"
            title="Export project"
            aria-label="Export project"
            data-testid="export-button"
          >
            ↓
          </button>
        )}
      </div>

      {/* ── Dropdown ────────────────────────────────────── */}
      {isOpen && (
        <div
          className="absolute left-0 right-0 z-40 mt-1 rounded-lg border border-gray-200 bg-white shadow-lg"
          role="listbox"
          data-testid="project-dropdown"
        >
          {/* Loading skeleton */}
          {isLoading && (
            <div className="space-y-2 p-3" aria-label="Loading projects">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className="h-4 animate-pulse rounded bg-gray-200"
                />
              ))}
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="p-3">
              <p className="mb-2 text-sm text-red-600" role="alert">
                Failed to load projects
              </p>
              <button
                onClick={() => refetch()}
                className="text-xs text-blue-600 hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Project list */}
          {!isLoading && !isError && (
            <ul className="max-h-64 overflow-y-auto">
              {(projects ?? []).map((p) => (
                <li key={p.id}>
                  <button
                    className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                      p.id === activeProjectId
                        ? "bg-blue-50 font-medium text-blue-700"
                        : "text-gray-700"
                    }`}
                    onClick={() => {
                      setActiveProject(p.id, p.title);
                      setIsOpen(false);
                    }}
                    role="option"
                    aria-selected={p.id === activeProjectId}
                  >
                    {p.title}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* New project button */}
          <div className="border-t border-gray-100 p-2">
            <button
              className="w-full rounded px-2 py-1.5 text-left text-sm text-blue-600 hover:bg-blue-50"
              onClick={() => {
                setIsOpen(false);
                setShowModal(true);
              }}
              data-testid="new-project-button"
            >
              + New Project
            </button>
          </div>
        </div>
      )}

      {/* ── Modal ───────────────────────────────────────── */}
      {showModal && (
        <NewProjectModal onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}
