import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../ui/Badge";
import type { AppNode } from "../../types";

type BadgeVariant = "source" | "artifact" | "chunk" | "project";

function nodeTypeToBadge(type: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    Source: "source",
    Artifact: "artifact",
    Chunk: "chunk",
    Project: "project",
  };
  return map[type] ?? "chunk";
}

// Keys rendered separately — excluded from the "extra" metadata section
const EXCLUDED_META_KEYS = new Set(["url", "content_body"]);

interface NodeDetailPanelProps {
  node: AppNode | null;
  onClose: () => void;
}

/**
 * Slide-in detail panel shown when a graph node is selected.
 *
 * Positioned absolutely over the right side of the canvas.
 * Renders nothing when `node` is null.
 * Shows all metadata key/value pairs in a collapsible section.
 */
export function NodeDetailPanel({ node, onClose }: NodeDetailPanelProps) {
  const [showAllMeta, setShowAllMeta] = useState(false);

  if (!node) return null;

  const createdDate = new Date(node.created_at * 1000).toLocaleDateString();
  const metaUrl =
    typeof node.metadata.url === "string" ? node.metadata.url : null;

  const extraMeta = Object.entries(node.metadata).filter(
    ([k, v]) => !EXCLUDED_META_KEYS.has(k) && v !== null && v !== undefined && v !== ""
  );

  return (
    <aside
      className="absolute right-0 top-0 z-10 flex h-full w-72 flex-col gap-3 overflow-y-auto border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-lg"
      data-testid="node-detail-panel"
    >
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 leading-snug">
          {node.title}
        </h2>
        <button
          onClick={onClose}
          className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700"
          aria-label="Close panel"
          data-testid="panel-close"
        >
          ×
        </button>
      </div>

      {/* ── Type badge ──────────────────────────────────── */}
      <Badge label={node.node_type} variant={nodeTypeToBadge(node.node_type)} />

      {/* ── Core metadata ───────────────────────────────── */}
      <p className="text-xs text-gray-400 dark:text-gray-500">Created: {createdDate}</p>

      {metaUrl && (
        <a
          href={metaUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="truncate text-xs text-blue-600 hover:underline"
          data-testid="meta-url"
        >
          → {metaUrl}
        </a>
      )}

      {/* ── Extra metadata (collapsible) ───────────────── */}
      {extraMeta.length > 0 && (
        <div>
          <button
            onClick={() => setShowAllMeta((v) => !v)}
            className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 underline"
          >
            {showAllMeta
              ? "Hide details"
              : `Show ${extraMeta.length} more field${extraMeta.length > 1 ? "s" : ""}`}
          </button>
          {showAllMeta && (
            <dl className="mt-2 space-y-1">
              {extraMeta.map(([k, v]) => (
                <div key={k} className="grid grid-cols-2 gap-1 text-xs">
                  <dt className="text-gray-500 dark:text-gray-400 truncate font-medium">{k}</dt>
                  <dd className="truncate text-gray-700 dark:text-gray-300">{String(v)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}

      {/* ── Actions ─────────────────────────────────────── */}
      <div className="mt-auto flex flex-col gap-2">
        {node.node_type === "Artifact" && (
          <Link
            to={`/drafts/${node.id}`}
            className="inline-block rounded bg-green-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-green-700"
            data-testid="open-draft-link"
          >
            Open Draft →
          </Link>
        )}
        {node.node_type === "Source" && metaUrl && (
          <a
            href={metaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded bg-blue-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-blue-700"
          >
            Open URL →
          </a>
        )}
      </div>
    </aside>
  );
}
