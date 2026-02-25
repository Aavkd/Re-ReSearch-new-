import { useEffect, useRef } from "react";
import { useCreateProject } from "../../hooks/useProjects";
import { useProjectStore } from "../../stores/projectStore";

interface NewProjectModalProps {
  onClose: () => void;
}

/**
 * Modal for creating a new project.
 *
 * - Submits via `useCreateProject` mutation.
 * - On success, sets the new project as active and closes.
 * - Closes on Escape key or backdrop click.
 */
export function NewProjectModal({ onClose }: NewProjectModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const { mutate, isPending, error, reset } = useCreateProject();

  // Auto-focus the input when modal opens
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const name = (inputRef.current?.value ?? "").trim();
    if (!name) return;
    mutate(name, {
      onSuccess: (node) => {
        setActiveProject(node.id, node.title);
        onClose();
      },
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          reset();
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-label="New project"
      data-testid="new-project-modal"
    >
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          New Project
        </h2>

        <form onSubmit={handleSubmit}>
          <label
            htmlFor="project-name-input"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            Project name
          </label>
          <input
            id="project-name-input"
            ref={inputRef}
            type="text"
            className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="My Research Project"
            disabled={isPending}
          />

          {error && (
            <p className="mb-2 text-sm text-red-600" role="alert">
              {error.message}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                reset();
                onClose();
              }}
              className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              disabled={isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={isPending}
            >
              {isPending ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
