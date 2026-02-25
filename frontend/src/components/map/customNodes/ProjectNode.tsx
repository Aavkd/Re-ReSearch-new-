import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";
import type { AppNode } from "../../../types";

export type ProjectNodeType = Node<{ label: string; raw: AppNode }, "projectNode">;

/**
 * React Flow custom node for Project-type graph nodes.
 * Renders a folder icon and the project title.
 */
export function ProjectNode({ data }: NodeProps<ProjectNodeType>) {
  return (
    <div className="flex min-w-[120px] items-center gap-2 rounded-lg border-2 border-purple-400 bg-purple-50 px-3 py-2 shadow-sm">
      <Handle type="target" position={Position.Left} />
      <span className="text-base">📁</span>
      <span className="truncate text-xs font-semibold text-purple-900">
        {data.label}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
