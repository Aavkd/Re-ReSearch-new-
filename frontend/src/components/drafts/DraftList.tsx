import { useState, useMemo } from "react";
import toast from "react-hot-toast";
import { useNodeList, useUpdateNode, useDeleteNode } from "../../hooks/useNodes";
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
 * - Search filter input at the top.
 * - Inline rename on double-click.
 * - Delete via Ã— button with confirmation toast.
 */
export function DraftList({ selectedNodeId, onSelect }: DraftListProps) {
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  const { data: allArtifacts, isLoading } = useNodeList("Artifact");
  const { data: graphData } = useProjectGraph(activeProjectId);
  const updateNode = useUpdateNode();
  const deleteNode = useDeleteNode();

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

  const filtered = useMemo(() => {
    if (!search.trim()) return drafts;
    const q = search.toLowerCase();
    return drafts.filter((d) => d.title.toLowerCase().includes(q));
  }, [drafts, search]);

  const startRename = (node: ArtifactNode) => {
    setRenamingId(node.id);
    setRenameValue(node.title);
  };

  const commitRename = async (node: ArtifactNode) => {
    const trimmed = renameValue.trim();
    setRenamingId(null);
    if (!trimmed || trimmed === node.title) return;
    try {
      await updateNode.mutateAsync({ id: node.id, payload: { title: trimmed } });
      toast.success("Draft renamed");
    } catch {
      toast.error("Failed to rename draft");
    }
  };

  const handleDelete = async (node: ArtifactNode) => {
    if (!window.confirm(`Delete "${node.title}"? This cannot be undone.`)) return;
    try {
      await deleteNode.mutateAsync(node.id);
      toast.success("Draft deleted");
    } catch {
      toast.error("Failed to delete draft");
    }
  };

  return (
    <aside
      className="flex w-72 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900"
      data-testid="draft-list"
    >
      {/* â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Drafts
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
          data-testid="new-draft-btn"
        >
          + New Draft
        </button>
      </div>

      {/* â”€â”€ Search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="border-b border-gray-200 dark:border-gray-700 px-3 py-2">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter draftsâ€¦"
          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-xs text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
          data-testid="draft-search"
        />
      </div>

      {/* â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex flex-col gap-1 p-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="p-4 text-xs text-gray-400 dark:text-gray-500" data-testid="empty-drafts">
            {search ? "No drafts match your filter." : "No drafts yet. Create one above."}
          </p>
        ) : (
          <ul>
            {filtered.map((node) => (
              <li key={node.id} className="group relative">
                {renamingId === node.id ? (
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => void commitRename(node)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void commitRename(node);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    className="w-full border-b border-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-2 text-sm text-gray-800 dark:text-gray-100 focus:outline-none"
                    data-testid={`draft-rename-input-${node.id}`}
                  />
                ) : (
                  <div className="flex items-center">
                    <button
                      onClick={() => onSelect(node)}
                      onDoubleClick={() => startRename(node)}
                      className={`flex-1 truncate px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800 ${
                        selectedNodeId === node.id
                          ? "bg-blue-50 dark:bg-blue-900/30 font-medium text-blue-800 dark:text-blue-300"
                          : "text-gray-700 dark:text-gray-300"
                      }`}
                      data-testid={`draft-item-${node.id}`}
                    >
                      {node.title}
                    </button>
                    {/* Actions â€” visible on hover */}
                    <div className="hidden group-hover:flex items-center pr-1 gap-0.5">
                      <button
                        onClick={() => startRename(node)}
                        title="Rename"
                        className="rounded p-1 text-xs text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                      >
                        âœï¸
                      </button>
                      <button
                        onClick={() => void handleDelete(node)}
                        title="Delete"
                        className="rounded p-1 text-xs text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        Ã—
                      </button>
                    </div>
                  </div>
                )}
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
