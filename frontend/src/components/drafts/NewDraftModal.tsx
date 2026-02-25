import { useState, useEffect } from "react";
import { useCreateNode } from "../../hooks/useNodes";
import { useProjectStore } from "../../stores/projectStore";
import { linkNodeToProject } from "../../api/projects";
import type { ArtifactNode } from "../../types";

interface NewDraftModalProps {
  onCreated: (node: ArtifactNode) => void;
  onClose: () => void;
}

/**
 * Modal for creating a new Artifact node and linking it to the active project.
 *
 * - Escape key and backdrop click close the modal.
 * - "Create" button disabled while mutation is pending.
 * - Inline error if mutation fails.
 */
export function NewDraftModal({ onCreated, onClose }: NewDraftModalProps) {
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const createNode = useCreateNode();

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setError(null);
    try {
      const node = await createNode.mutateAsync({
        node_type: "Artifact",
        title: title.trim(),
      });
      // Link the new node to the active project
      if (activeProjectId) {
        await linkNodeToProject(activeProjectId, node.id, "HAS_ARTIFACT");
      }
      onCreated(node as ArtifactNode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create draft.");
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-20 bg-black/30"
        onClick={onClose}
        data-testid="modal-backdrop"
      />

      {/* Modal */}
      <div
        className="fixed left-1/2 top-1/3 z-30 w-80 -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl"
        data-testid="new-draft-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-draft-title"
      >
        <h2
          id="new-draft-title"
          className="mb-4 text-sm font-semibold text-gray-800"
        >
          New Draft
        </h2>

        <label className="mb-1 block text-xs text-gray-600" htmlFor="draft-title">
          Draft title
        </label>
        <input
          id="draft-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="Untitled draft"
          className="mb-3 w-full rounded border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          data-testid="draft-title-input"
          autoFocus
        />

        {error && (
          <p className="mb-2 text-xs text-red-600" data-testid="create-error">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!title.trim() || createNode.isPending}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="create-btn"
          >
            {createNode.isPending ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </>
  );
}
