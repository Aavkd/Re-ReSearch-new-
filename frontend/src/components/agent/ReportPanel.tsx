import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link } from "react-router-dom";

interface ReportPanelProps {
  report: string | null;
  artifactId: string | null;
}

/**
 * ReportPanel — renders the final research report as Markdown.
 *
 * - Invisible (`null`) when report is not yet available.
 * - "View in Map →" link navigates to `/map` when `artifactId` is set.
 * - "Copy Report" copies the raw Markdown to the clipboard.
 */
export function ReportPanel({ report, artifactId }: ReportPanelProps) {
  if (!report) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(report).catch(() => {
      /* ignore clipboard errors in non-secure contexts */
    });
  };

  return (
    <div
      data-testid="report-panel"
      className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
    >
      {/* ── Actions ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-gray-700">Research Report</h3>
        <div className="flex items-center gap-2">
          {artifactId && (
            <Link
              to="/map"
              data-testid="view-in-map-link"
              className="text-sm text-blue-600 hover:underline"
            >
              View in Map →
            </Link>
          )}
          <button
            type="button"
            data-testid="copy-report-button"
            onClick={handleCopy}
            className="rounded border border-gray-300 px-3 py-1 text-xs
                       text-gray-600 hover:bg-gray-50"
          >
            Copy Report
          </button>
        </div>
      </div>

      {/* ── Rendered Markdown ──────────────────────────────────────────── */}
      <article
        data-testid="report-content"
        className="prose prose-sm max-w-none"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </article>
    </div>
  );
}
