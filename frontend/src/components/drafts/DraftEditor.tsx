import { useEffect, useRef, useState, useCallback } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { markdown } from "@codemirror/lang-markdown";
import { oneDark } from "@codemirror/theme-one-dark";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSettingsStore } from "../../stores/settingsStore";
import type { ArtifactNode } from "../../types";

// ── Types ─────────────────────────────────────────────────────────────────

interface DraftEditorProps {
  node: ArtifactNode;
  onSave: (content: string) => Promise<void> | void;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";
type ViewMode = "edit" | "preview" | "split";

// ── Component ─────────────────────────────────────────────────────────────

/**
 * CodeMirror 6 Markdown editor for an Artifact node.
 *
 * Modes: Edit | Preview (react-markdown) | Split (side by side).
 * Saving: auto-save on blur + Ctrl/Cmd+S.
 * Dark mode: applies @codemirror/theme-one-dark when theme is "dark".
 */
export function DraftEditor({ node, onSave }: DraftEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onSaveRef = useRef(onSave);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [previewContent, setPreviewContent] = useState<string>("");
  const { theme } = useSettingsStore();

  const isDark = theme === "dark" ||
    (theme === "system" && typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  // Keep callback ref fresh without re-creating the editor
  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  const triggerSave = useCallback(async (view: EditorView) => {
    const content = view.state.doc.toString();
    setSaveStatus("saving");
    // Update preview content whenever saving
    setPreviewContent(content);
    try {
      await onSaveRef.current(content);
      setSaveStatus("saved");
      // Reset to idle after 3 s
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    }
  }, []);

  // Create / destroy the editor when the node or theme changes
  useEffect(() => {
    if (!containerRef.current) return;
    if (viewMode === "preview") return; // nothing to mount

    const initialContent =
      typeof node.metadata.content_body === "string"
        ? node.metadata.content_body
        : "";

    // Sync preview content with initial value
    setPreviewContent(initialContent);

    const state = EditorState.create({
      doc: initialContent,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        markdown(),
        ...(isDark ? [oneDark] : []),
        keymap.of([
          {
            key: "Ctrl-s",
            mac: "Cmd-s",
            run: (view) => { void triggerSave(view); return true; },
          },
        ]),
        EditorView.domEventHandlers({
          blur: (_event, view) => { void triggerSave(view); },
        }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged && viewMode === "split") {
            setPreviewContent(update.state.doc.toString());
          }
        }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "14px" },
          ".cm-scroller": { fontFamily: "monospace", overflow: "auto" },
        }),
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.id, viewMode, isDark]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  const wordCount = previewContent.trim()
    ? previewContent.trim().split(/\s+/).length
    : 0;

  const statusLabel =
    saveStatus === "saving"
      ? "Saving…"
      : saveStatus === "saved"
        ? "Saved ✓"
        : saveStatus === "error"
          ? "Save failed"
          : null;

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden" data-testid="draft-editor">
      {/* ── Toolbar ────────────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-1.5">
        {/* View mode buttons */}
        <div className="flex gap-1">
          {(["edit", "preview", "split"] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`rounded px-2 py-0.5 text-xs capitalize transition-colors ${
                viewMode === mode
                  ? "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 font-medium"
                  : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        {/* Status + word count */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 dark:text-gray-500">{wordCount} words</span>
          {statusLabel && (
            <span
              className={`rounded px-2 py-0.5 text-xs ${
                saveStatus === "error"
                  ? "bg-red-100 text-red-700"
                  : "bg-green-100 text-green-700"
              }`}
              data-testid="save-status"
            >
              {statusLabel}
            </span>
          )}
        </div>
      </div>

      {/* ── Content area ───────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Editor pane */}
        {(viewMode === "edit" || viewMode === "split") && (
          <div
            ref={containerRef}
            className={`overflow-auto ${viewMode === "split" ? "w-1/2 border-r border-gray-200 dark:border-gray-700" : "flex-1"}`}
            data-testid="cm-container"
          />
        )}

        {/* Preview pane */}
        {(viewMode === "preview" || viewMode === "split") && (
          <div
            className={`overflow-y-auto p-4 ${viewMode === "split" ? "w-1/2" : "flex-1"}`}
            data-testid="preview-pane"
          >
            <article className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewContent}</ReactMarkdown>
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
