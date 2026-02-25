import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";
import type { AppNode } from "../../../types";

export type ArtifactNodeType = Node<
  { label: string; raw: AppNode },
  "artifactNode"
>;

/**
 * React Flow custom node for Artifact-type graph nodes.
 * Renders a scroll icon and the artifact title. Green border.
 */
export function ArtifactNode({ data }: NodeProps<ArtifactNodeType>) {
  return (
    <div className="flex min-w-[140px] items-center gap-2 rounded-lg border-2 border-green-400 bg-green-50 px-3 py-2 shadow-sm">
      <Handle type="target" position={Position.Left} />
      <span className="text-base">📜</span>
      <span className="truncate text-xs font-medium text-green-900">
        {data.label}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
