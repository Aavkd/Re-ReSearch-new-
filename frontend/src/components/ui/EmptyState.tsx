import type { ReactNode } from "react";

interface EmptyStateProps {
  message: string;
  action?: ReactNode;
}

/**
 * EmptyState — centred placeholder block shown when a list or view has no content.
 * Used across Library, Map, Drafts, and Agent screens.
 */
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
    >
      <p className="text-sm text-gray-500">{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
