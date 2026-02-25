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

interface NodeResultCardProps {
  node: AppNode;
}

/**
 * A single row in the search-results list.
 *
 * - Colour-coded type badge via the shared Badge component.
 * - Snippet toggles between truncated and expanded on click.
 * - Source nodes with a URL get an "Open URL" link.
 * - Artifact nodes get an "→ Open Draft" link.
 */
export function NodeResultCard({ node }: NodeResultCardProps) {
  const [expanded, setExpanded] = useState(false);

  const snippet =
    typeof node.metadata.snippet === "string" ? node.metadata.snippet : null;
  const metaUrl =
    typeof node.metadata.url === "string" ? node.metadata.url : null;

  const createdDate = new Date(
    typeof node.created_at === "number" ? node.created_at * 1000 : node.created_at
  ).toLocaleDateString();

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white dark:bg-gray-800 dark:border-gray-700 p-4 shadow-sm"
      data-testid="node-result-card"
    >
      <div className="mb-1 flex items-center gap-2">
        <Badge label={node.node_type} variant={nodeTypeToBadge(node.node_type)} />
        <span className="text-xs text-gray-400 dark:text-gray-500">{createdDate}</span>
      </div>

      <p className="mb-1 font-medium text-gray-900 dark:text-gray-100">{node.title}</p>

      {snippet && (
        <p
          className={`mb-1 text-sm text-gray-500 dark:text-gray-400 cursor-pointer ${
            expanded ? "" : "line-clamp-2"
          }`}
          onClick={() => setExpanded((e) => !e)}
          title={expanded ? "Click to collapse" : "Click to expand"}
        >
          {snippet}
        </p>
      )}

      <div className="mt-2 flex flex-wrap gap-3">
        {node.node_type === "Artifact" && (
          <Link
            to={`/drafts/${node.id}`}
            className="text-sm text-blue-600 hover:underline"
          >
            → Open Draft
          </Link>
        )}
        {node.node_type === "Source" && metaUrl && (
          <a
            href={metaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline"
          >
            → Open URL
          </a>
        )}
      </div>
    </div>
  );
}
