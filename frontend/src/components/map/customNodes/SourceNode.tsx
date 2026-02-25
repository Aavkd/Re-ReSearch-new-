import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";
import type { AppNode } from "../../../types";

export type SourceNodeType = Node<{ label: string; raw: AppNode }, "sourceNode">;

/**
 * React Flow custom node for Source-type graph nodes.
 * Renders a document icon and the source title (truncated at 30 chars).
 * Blue border.
 */
export function SourceNode({ data }: NodeProps<SourceNodeType>) {
  const label =
    data.label.length > 30 ? data.label.slice(0, 30) + "…" : data.label;

  return (
    <div className="flex min-w-[140px] items-center gap-2 rounded-lg border-2 border-blue-400 bg-blue-50 px-3 py-2 shadow-sm">
      <Handle type="target" position={Position.Left} />
      <span className="text-base">📄</span>
      <span className="truncate text-xs font-medium text-blue-900">{label}</span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
