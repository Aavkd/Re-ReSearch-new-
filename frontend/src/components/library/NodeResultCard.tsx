import { Link } from "react-router-dom";
import type { AppNode } from "../../types";

interface NodeResultCardProps {
  node: AppNode;
}

/**
 * A single row in the search-results list.
 *
 * - Colour-coded type badge: Source = blue, Artifact = green, Chunk = grey.
 * - Shows title, optional snippet from `metadata.snippet`, and creation date.
 * - Artifact nodes include a "→ Open Draft" link to `/drafts/{id}`.
 */
export function NodeResultCard({ node }: NodeResultCardProps) {
  const badgeClass =
    node.node_type === "Artifact"
      ? "bg-green-100 text-green-800"
      : node.node_type === "Source"
        ? "bg-blue-100 text-blue-800"
        : "bg-gray-100 text-gray-700";

  const snippet =
    typeof node.metadata.snippet === "string" ? node.metadata.snippet : null;

  const createdDate = new Date(
    typeof node.created_at === "number" ? node.created_at * 1000 : node.created_at
  ).toLocaleDateString();

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      data-testid="node-result-card"
    >
      <div className="mb-1 flex items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}
        >
          {node.node_type}
        </span>
        <span className="text-xs text-gray-400">{createdDate}</span>
      </div>

      <p className="mb-1 font-medium text-gray-900">{node.title}</p>

      {snippet && (
        <p className="mb-1 truncate text-sm text-gray-500">{snippet}</p>
      )}

      {node.node_type === "Artifact" && (
        <Link
          to={`/drafts/${node.id}`}
          className="mt-1 inline-block text-sm text-blue-600 hover:underline"
        >
          → Open Draft
        </Link>
      )}
    </div>
  );
}
