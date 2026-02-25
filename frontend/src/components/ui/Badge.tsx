type BadgeVariant = "source" | "artifact" | "chunk" | "project";

interface BadgeProps {
  label: string;
  variant: BadgeVariant;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  source: "bg-blue-100 text-blue-800",
  artifact: "bg-green-100 text-green-800",
  chunk: "bg-gray-100 text-gray-700",
  project: "bg-purple-100 text-purple-800",
};

/**
 * Badge — coloured pill that identifies a node type.
 * Used in NodeResultCard and NodeDetailPanel.
 */
export function Badge({ label, variant }: BadgeProps) {
  return (
    <span
      data-testid={`badge-${variant}`}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium
                  ${VARIANT_CLASSES[variant]}`}
    >
      {label}
    </span>
  );
}
