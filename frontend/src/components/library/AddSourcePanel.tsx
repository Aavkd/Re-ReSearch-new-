import { useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { ingestUrl, ingestPdf } from "../../api/library";
import { linkNodeToProject } from "../../api/projects";
import { useProjectStore } from "../../stores/projectStore";

type Tab = "url" | "pdf";

type UrlResult =
  | { url: string; status: "pending" }
  | { url: string; status: "success"; title: string }
  | { url: string; status: "error"; message: string };

/**
 * Panel for adding sources to the knowledge base.
 *
 * Two tabs:
 *  - **URL**: textarea (one URL per line) â†’ batch POST /ingest/url â†’ links to active project.
 *  - **PDF**: file input â†’ POST /ingest/pdf â†’ links to active project.
 */
export function AddSourcePanel() {
  const [tab, setTab] = useState<Tab>("url");
  const [urlsInput, setUrlsInput] = useState("");
  const [urlResults, setUrlResults] = useState<UrlResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<
    | { type: "idle" }
    | { type: "loading" }
    | { type: "success"; title: string }
    | { type: "error"; message: string }
  >({ type: "idle" });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  const afterIngest = async (nodeId: string) => {
    if (activeProjectId) {
      await linkNodeToProject(activeProjectId, nodeId);
      queryClient.invalidateQueries({ queryKey: ["projectGraph", activeProjectId] });
    }
    queryClient.invalidateQueries({ queryKey: ["nodes"] });
    queryClient.invalidateQueries({ queryKey: ["projectNodes", activeProjectId] });
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = urlsInput
      .split("\n")
      .map((u) => u.trim())
      .filter(Boolean);
    if (!urls.length || !activeProjectId) return;

    // Initialise results as pending
    setUrlResults(urls.map((url) => ({ url, status: "pending" })));
    setIsLoading(true);

    const settled = await Promise.allSettled(
      urls.map((url) => ingestUrl(url).then((r) => ({ url, result: r })))
    );

    const next: UrlResult[] = await Promise.all(
      settled.map(async (s, i) => {
        const url = urls[i];
        if (s.status === "fulfilled") {
          try {
            await afterIngest(s.value.result.node_id);
          } catch {
            /* link errors are non-fatal */
          }
          return { url, status: "success", title: s.value.result.title } as UrlResult;
        } else {
          const msg =
            s.reason instanceof Error ? s.reason.message : "Ingest failed";
          return { url, status: "error", message: msg } as UrlResult;
        }
      })
    );

    setUrlResults(next);
    setIsLoading(false);

    const successes = next.filter((r) => r.status === "success").length;
    const failures = next.filter((r) => r.status === "error").length;
    if (successes) toast.success(`${successes} source${successes > 1 ? "s" : ""} added`);
    if (failures) toast.error(`${failures} URL${failures > 1 ? "s" : ""} failed`);
    if (successes > 0) setUrlsInput("");
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeProjectId) return;
    setPdfStatus({ type: "loading" });
    try {
      const result = await ingestPdf(file);
      await afterIngest(result.node_id);
      setPdfStatus({ type: "success", title: result.title });
      toast.success(`PDF added: ${result.title}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Ingest failed";
      setPdfStatus({ type: "error", message: msg });
      toast.error(msg);
    }
  };

  return (
    <div
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm"
      data-testid="add-source-panel"
    >
      <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Add Source</h2>

      {/* Tab switcher */}
      <div className="mb-3 flex gap-2 border-b border-gray-200 dark:border-gray-700">
        {(["url", "pdf"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setUrlResults([]);
              setPdfStatus({ type: "idle" });
            }}
            className={`pb-2 text-sm font-medium transition-colors ${
              tab === t
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
            data-testid={`tab-${t}`}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {/* URL tab */}
      {tab === "url" && (
        <form onSubmit={handleUrlSubmit} className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 dark:text-gray-400">
            Enter one URL per line
          </label>
          <textarea
            value={urlsInput}
            onChange={(e) => setUrlsInput(e.target.value)}
            placeholder={"https://example.com/article\nhttps://another.com/page"}
            rows={4}
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 dark:disabled:bg-gray-850 resize-y"
            disabled={!activeProjectId || isLoading}
            aria-label="URLs to ingest"
            data-testid="url-input"
          />
          <button
            type="submit"
            className="self-end rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={!activeProjectId || !urlsInput.trim() || isLoading}
            data-testid="url-add-button"
          >
            {isLoading ? "Addingâ€¦" : "Add"}
          </button>

          {/* Per-URL results */}
          {urlResults.length > 0 && (
            <ul className="mt-1 flex flex-col gap-1 text-xs">
              {urlResults.map((r) => (
                <li key={r.url} className="flex items-start gap-1.5">
                  {r.status === "pending" && (
                    <span className="mt-0.5 h-2 w-2 animate-pulse rounded-full bg-gray-300" />
                  )}
                  {r.status === "success" && (
                    <span className="text-green-600">âœ“</span>
                  )}
                  {r.status === "error" && (
                    <span className="text-red-500">âœ—</span>
                  )}
                  <span className="truncate text-gray-500 dark:text-gray-400">{r.url}</span>
                  {r.status === "success" && (
                    <span className="shrink-0 text-green-600">{r.title}</span>
                  )}
                  {r.status === "error" && (
                    <span className="shrink-0 text-red-500">{r.message}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </form>
      )}

      {/* PDF tab */}
      {tab === "pdf" && (
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500 dark:text-gray-400">
            {activeProjectId
              ? "Select a PDF file to upload"
              : "Select a project first to upload files"}
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={!activeProjectId || pdfStatus.type === "loading"}
            className="text-sm text-gray-600 file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            data-testid="pdf-input"
          />
          {pdfStatus.type === "success" && (
            <p className="text-sm text-green-600" role="status" data-testid="ingest-success">
              âœ“ Added: {pdfStatus.title}
            </p>
          )}
          {pdfStatus.type === "error" && (
            <p className="text-sm text-red-600" role="alert" data-testid="ingest-error">
              {pdfStatus.message}
            </p>
          )}
        </div>
      )}

      {!activeProjectId && (
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Select a project to add sources.
        </p>
      )}
    </div>
  );
}
