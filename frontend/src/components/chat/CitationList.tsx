import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp } from "lucide-react";

interface CitationListProps {
  citations: Array<{ id: string; title: string; url?: string }>;
}

/**
 * CitationList — collapsible "Sources" panel displayed after an assistant reply.
 *
 * Clicking a citation with a URL opens it in a new tab.
 * Clicking one without a URL navigates to /library and passes the node ID
 * via router state so LibraryScreen can highlight it.
 *
 * Hidden entirely when citations array is empty.
 */
export function CitationList({ citations }: CitationListProps) {
  const [open, setOpen] = useState(true);
  const navigate = useNavigate();

  if (citations.length === 0) return null;

  return (
    <div
      className="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-sm"
      data-testid="citation-list"
    >
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        Sources ({citations.length})
        {open ? (
          <ChevronUp size={14} aria-hidden="true" />
        ) : (
          <ChevronDown size={14} aria-hidden="true" />
        )}
      </button>

      {open && (
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {citations.map((c) => (
            <li key={c.id}>
              <button
                className="w-full px-3 py-2 text-left text-xs text-blue-600 dark:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 truncate transition-colors"
                onClick={() => {
                  if (c.url) {
                    window.open(c.url, "_blank", "noopener,noreferrer");
                  } else {
                    navigate("/library", { state: { nodeId: c.id } });
                  }
                }}
                title={c.title}
              >
                {c.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
