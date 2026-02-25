import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { DraftList } from "../components/drafts/DraftList";
import { DraftEditor } from "../components/drafts/DraftEditor";
import { useNode } from "../hooks/useNodes";
import { useUpdateNode } from "../hooks/useNodes";
import { useProjectStore } from "../stores/projectStore";
import type { ArtifactNode } from "../types";

/**
 * Drafts screen — split-pane view with an artifact list on the left and a
 * Markdown editor on the right.
 *
 * - If the URL contains `:nodeId`, that draft is auto-selected on mount.
 * - `onSave` updates `metadata.content_body` via `PUT /nodes/{id}`.
 * - No-project guard: prompts the user to select a project first.
 */
export function DraftsScreen() {
  const { nodeId: urlNodeId } = useParams<{ nodeId?: string }>();
  const [selectedNode, setSelectedNode] = useState<ArtifactNode | null>(null);

  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const updateNode = useUpdateNode();

  // Auto-select if navigated directly to /drafts/:nodeId
  const { data: urlNode } = useNode(urlNodeId ?? null);
  useEffect(() => {
    if (urlNode && urlNode.node_type === "Artifact") {
      setSelectedNode(urlNode as ArtifactNode);
    }
  }, [urlNode]);

  const handleSave = async (content: string) => {
    if (!selectedNode) return;
    await updateNode.mutateAsync({
      id: selectedNode.id,
      payload: {
        metadata: { ...selectedNode.metadata, content_body: content },
      },
    });
  };

  // ── No project guard ───────────────────────────────────────────────────
  if (!activeProjectId) {
    return (
      <div
        className="flex flex-1 items-center justify-center text-sm text-gray-400"
        data-testid="drafts-screen"
      >
        Select a project in the sidebar to get started.
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 overflow-hidden"
      data-testid="drafts-screen"
    >
      {/* ── Left panel ────────────────────────────────────────────────── */}
      <DraftList
        selectedNodeId={selectedNode?.id ?? null}
        onSelect={setSelectedNode}
      />

      {/* ── Right panel ───────────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {selectedNode ? (
          <DraftEditor node={selectedNode} onSave={handleSave} />
        ) : (
          <div
            className="flex flex-1 items-center justify-center text-sm text-gray-400"
            data-testid="no-draft-selected"
          >
            No draft selected. Choose one from the list or create a new draft.
          </div>
        )}
      </main>
    </div>
  );
}
