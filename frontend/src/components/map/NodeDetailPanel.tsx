import { Link } from "react-router-dom";
import type { AppNode } from "../../types";

interface NodeDetailPanelProps {
  node: AppNode | null;
  onClose: () => void;
}

/**
 * Slide-in detail panel shown when a graph node is selected.
 *
 * Positioned absolutely over the right side of the canvas.
 * Renders nothing when `node` is null.
 */
export function NodeDetailPanel({ node, onClose }: NodeDetailPanelProps) {
  if (!node) return null;

  const createdDate = new Date(node.created_at * 1000).toLocaleDateString();
  const metaUrl =
    typeof node.metadata.url === "string" ? node.metadata.url : null;

  return (
    <aside
      className="absolute right-0 top-0 z-10 flex h-full w-72 flex-col gap-3 overflow-y-auto border-l border-gray-200 bg-white p-4 shadow-lg"
      data-testid="node-detail-panel"
    >
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-800 leading-snug">
          {node.title}
        </h2>
        <button
          onClick={onClose}
          className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Close panel"
          data-testid="panel-close"
        >
          ×
        </button>
      </div>

      {/* ── Type badge ──────────────────────────────────── */}
      <span
        className={`self-start rounded-full px-2 py-0.5 text-xs font-medium ${
          node.node_type === "Artifact"
            ? "bg-green-100 text-green-800"
            : node.node_type === "Source"
              ? "bg-blue-100 text-blue-800"
              : "bg-purple-100 text-purple-800"
        }`}
      >
        {node.node_type}
      </span>

      {/* ── Metadata ────────────────────────────────────── */}
      <p className="text-xs text-gray-400">Created: {createdDate}</p>

      {metaUrl && (
        <a
          href={metaUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="truncate text-xs text-blue-600 hover:underline"
          data-testid="meta-url"
        >
          {metaUrl}
        </a>
      )}

      {/* ── Artifact-only action ────────────────────────── */}
      {node.node_type === "Artifact" && (
        <Link
          to={`/drafts/${node.id}`}
          className="mt-auto inline-block rounded bg-green-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-green-700"
          data-testid="open-draft-link"
        >
          Open Draft →
        </Link>
      )}
    </aside>
  );
}
