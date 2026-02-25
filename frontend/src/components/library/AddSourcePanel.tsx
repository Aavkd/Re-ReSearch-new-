import { useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ingestUrl, ingestPdf } from "../../api/library";
import { linkNodeToProject } from "../../api/projects";
import { useProjectStore } from "../../stores/projectStore";

type Tab = "url" | "pdf";

/**
 * Panel for adding sources to the knowledge base.
 *
 * Two tabs:
 *  - **URL**: text input → POST /ingest/url → links to active project.
 *  - **PDF**: file input → POST /ingest/pdf → links to active project.
 *
 * After a successful ingest, the `['nodes']` and `['projectGraph', id]`
 * query keys are invalidated so the rest of the UI refreshes automatically.
 *
 * The "Add" / file-select control is disabled when no project is active.
 */
export function AddSourcePanel() {
  const [tab, setTab] = useState<Tab>("url");
  const [urlInput, setUrlInput] = useState("");
  const [status, setStatus] = useState<
    | { type: "idle" }
    | { type: "loading" }
    | { type: "success"; title: string }
    | { type: "error"; message: string }
  >({ type: "idle" });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  const afterIngest = async (nodeId: string, title: string) => {
    if (activeProjectId) {
      await linkNodeToProject(activeProjectId, nodeId);
      queryClient.invalidateQueries({
        queryKey: ["projectGraph", activeProjectId],
      });
    }
    queryClient.invalidateQueries({ queryKey: ["nodes"] });
    queryClient.invalidateQueries({ queryKey: ["projectNodes", activeProjectId] });
    setStatus({ type: "success", title });
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = urlInput.trim();
    if (!url || !activeProjectId) return;
    setStatus({ type: "loading" });
    try {
      const result = await ingestUrl(url);
      await afterIngest(result.node_id, result.title);
      setUrlInput("");
    } catch (err) {
      setStatus({
        type: "error",
        message: err instanceof Error ? err.message : "Ingest failed",
      });
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeProjectId) return;
    setStatus({ type: "loading" });
    try {
      const result = await ingestPdf(file);
      await afterIngest(result.node_id, result.title);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setStatus({
        type: "error",
        message: err instanceof Error ? err.message : "Ingest failed",
      });
    }
  };

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      data-testid="add-source-panel"
    >
      <h2 className="mb-3 text-sm font-semibold text-gray-700">Add Source</h2>

      {/* Tab switcher */}
      <div className="mb-3 flex gap-2 border-b border-gray-200">
        {(["url", "pdf"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setStatus({ type: "idle" });
            }}
            className={`pb-2 text-sm font-medium transition-colors ${
              tab === t
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
            data-testid={`tab-${t}`}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {/* URL tab */}
      {tab === "url" && (
        <form onSubmit={handleUrlSubmit} className="flex gap-2">
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/article"
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50"
            disabled={!activeProjectId || status.type === "loading"}
            aria-label="URL to ingest"
            data-testid="url-input"
          />
          <button
            type="submit"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={!activeProjectId || !urlInput.trim() || status.type === "loading"}
            data-testid="url-add-button"
          >
            {status.type === "loading" ? "Adding…" : "Add"}
          </button>
        </form>
      )}

      {/* PDF tab */}
      {tab === "pdf" && (
        <div className="flex flex-col gap-2">
          <label className="text-xs text-gray-500">
            {activeProjectId
              ? "Select a PDF file to upload"
              : "Select a project first to upload files"}
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={!activeProjectId || status.type === "loading"}
            className="text-sm text-gray-600 file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            data-testid="pdf-input"
          />
        </div>
      )}

      {/* Status feedback */}
      {status.type === "success" && (
        <p className="mt-2 text-sm text-green-600" role="status" data-testid="ingest-success">
          ✓ Added: {status.title}
        </p>
      )}
      {status.type === "error" && (
        <p className="mt-2 text-sm text-red-600" role="alert" data-testid="ingest-error">
          {status.message}
        </p>
      )}

      {!activeProjectId && (
        <p className="mt-2 text-xs text-gray-400">
          Select a project to add sources.
        </p>
      )}
    </div>
  );
}
