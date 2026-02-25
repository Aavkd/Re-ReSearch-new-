import { useState, useMemo } from "react";
import { useNodeList } from "../../hooks/useNodes";
import { useProjectGraph } from "../../hooks/useProjectGraph";
import { useProjectStore } from "../../stores/projectStore";
import { NewDraftModal } from "./NewDraftModal";
import type { ArtifactNode } from "../../types";

interface DraftListProps {
  selectedNodeId: string | null;
  onSelect: (node: ArtifactNode) => void;
}

/**
 * Left panel listing Artifact nodes that belong to the active project.
 *
 * - Loads all Artifact nodes via `useNodeList("Artifact")`.
 * - Filters client-side to those in the active project's graph node id set.
 * - "+ New Draft" opens NewDraftModal.
 */
export function DraftList({ selectedNodeId, onSelect }: DraftListProps) {
  const [showModal, setShowModal] = useState(false);

  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  // All artifact nodes (global)
  const { data: allArtifacts, isLoading } = useNodeList("Artifact");

  // Project graph to get the node id set for this project
  const { data: graphData } = useProjectGraph(activeProjectId);

  // Filter to only artifacts that appear in the active project's graph
  const projectNodeIds = useMemo(
    () => new Set((graphData?.nodes ?? []).map((n) => n.id)),
    [graphData]
  );

  const drafts = useMemo(() => {
    if (!activeProjectId) return [];
    return (allArtifacts ?? []).filter(
      (n): n is ArtifactNode =>
        n.node_type === "Artifact" &&
        (projectNodeIds.size === 0 || projectNodeIds.has(n.id))
    );
  }, [allArtifacts, projectNodeIds, activeProjectId]);

  return (
    <aside
      className="flex w-72 shrink-0 flex-col border-r border-gray-200 bg-gray-50"
      data-testid="draft-list"
    >
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Drafts
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
          data-testid="new-draft-btn"
        >
          + New Draft
        </button>
      </div>

      {/* ── List ───────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          // Loading skeleton
          <div className="flex flex-col gap-1 p-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-8 animate-pulse rounded bg-gray-200"
              />
            ))}
          </div>
        ) : drafts.length === 0 ? (
          <p className="p-4 text-xs text-gray-400" data-testid="empty-drafts">
            No drafts yet. Create one above.
          </p>
        ) : (
          <ul>
            {drafts.map((node) => (
              <li key={node.id}>
                <button
                  onClick={() => onSelect(node)}
                  className={`w-full truncate px-3 py-2 text-left text-sm hover:bg-gray-100 ${
                    selectedNodeId === node.id
                      ? "bg-blue-50 font-medium text-blue-800"
                      : "text-gray-700"
                  }`}
                  data-testid={`draft-item-${node.id}`}
                >
                  {node.title}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {showModal && (
        <NewDraftModal
          onCreated={(node) => {
            onSelect(node);
            setShowModal(false);
          }}
          onClose={() => setShowModal(false)}
        />
      )}
    </aside>
  );
}
