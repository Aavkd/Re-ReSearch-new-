import { useEffect, useRef, useState } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { markdown } from "@codemirror/lang-markdown";
import type { ArtifactNode } from "../../types";

// ── Types ─────────────────────────────────────────────────────────────────

interface DraftEditorProps {
  node: ArtifactNode;
  onSave: (content: string) => void;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

// ── Component ─────────────────────────────────────────────────────────────

/**
 * CodeMirror 6 Markdown editor for an Artifact node.
 *
 * Content is stored in and read from `node.metadata.content_body`.
 * Saving:
 *   - Auto-save on blur.
 *   - Ctrl+S / Cmd+S keyboard shortcut.
 * Status indicator in the top-right corner.
 */
export function DraftEditor({ node, onSave }: DraftEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onSaveRef = useRef(onSave);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");

  // Keep callback ref fresh without re-creating the editor
  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  // Create / destroy the editor when the node changes
  useEffect(() => {
    if (!containerRef.current) return;

    const initialContent =
      typeof node.metadata.content_body === "string"
        ? node.metadata.content_body
        : "";

    const triggerSave = (view: EditorView) => {
      const content = view.state.doc.toString();
      setSaveStatus("saving");
      try {
        onSaveRef.current(content);
        setSaveStatus("saved");
      } catch {
        setSaveStatus("error");
      }
      return true; // signal keymap handled
    };

    const state = EditorState.create({
      doc: initialContent,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        markdown(),
        // Ctrl+S / Cmd+S save
        keymap.of([
          {
            key: "Ctrl-s",
            mac: "Cmd-s",
            run: (view) => triggerSave(view),
          },
        ]),
        // Auto-save on blur
        EditorView.domEventHandlers({
          blur: (_event, view) => {
            triggerSave(view);
          },
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
    // Re-create editor only when the node ID changes — not on every save callback update
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.id]);

  // Save-status display text
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
      {/* Save status indicator */}
      {statusLabel && (
        <div
          className={`absolute right-3 top-2 z-10 rounded px-2 py-0.5 text-xs ${
            saveStatus === "error"
              ? "bg-red-100 text-red-700"
              : "bg-green-100 text-green-700"
          }`}
          data-testid="save-status"
        >
          {statusLabel}
        </div>
      )}

      {/* CodeMirror container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto"
        data-testid="cm-container"
      />
    </div>
  );
}
