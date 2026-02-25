import { useState, useRef, useEffect } from "react";
import { GoalForm } from "../components/agent/GoalForm";
import { ProgressFeed } from "../components/agent/ProgressFeed";
import { ReportPanel } from "../components/agent/ReportPanel";
import { streamResearch } from "../api/agent";
import { linkNodeToProject } from "../api/projects";
import { useProjectStore } from "../stores/projectStore";
import type { ResearchDepth, SseEvent, SseNodeEvent, SseDoneEvent } from "../types";

/**
 * AgentScreen — streaming research runner.
 *
 * - GoalForm submits a goal + depth to the agent.
 * - ProgressFeed shows live SSE node events during the run.
 * - ReportPanel renders the final markdown report.
 * - On completion, the artifact is linked to the active project (fire-and-forget).
 * - useEffect cleanup aborts any in-flight SSE stream on unmount.
 */
export function AgentScreen() {
  const [events, setEvents] = useState<SseNodeEvent[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  // Abort stream on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const handleSubmit = (goal: string, depth: ResearchDepth) => {
    // Reset previous run state
    setEvents([]);
    setReport(null);
    setArtifactId(null);
    setError(null);
    setIsRunning(true);

    const abort = streamResearch(
      goal,
      depth,
      // onEvent — called for every SSE event (node, done, error)
      (e: SseEvent) => {
        if (e.event === "node") {
          setEvents((prev) => [...prev, e as SseNodeEvent]);
        } else if (e.event === "done") {
          const done = e as SseDoneEvent;
          setReport(done.report);
          setArtifactId(done.artifact_id);
          // Fire-and-forget: link artifact to active project
          if (activeProjectId) {
            linkNodeToProject(
              activeProjectId,
              done.artifact_id,
              "HAS_ARTIFACT"
            ).catch(() => {
              // Ignore link errors — not critical to the research flow
            });
          }
        }
      },
      // onDone
      () => {
        setIsRunning(false);
      },
      // onError
      (err: Error) => {
        setError(err.message);
        setIsRunning(false);
      }
    );

    abortRef.current = abort;
  };

  return (
    <div
      className="flex flex-1 flex-col gap-5 overflow-y-auto p-6"
      data-testid="agent-screen"
    >
      <h1 className="text-lg font-semibold text-gray-800">Agent Research</h1>

      <GoalForm onSubmit={handleSubmit} isRunning={isRunning} />

      {/* ── Error banner ─────────────────────────────────────────────── */}
      {error && (
        <div
          role="alert"
          data-testid="error-banner"
          className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* ── Live progress ────────────────────────────────────────────── */}
      {events.length > 0 && (
        <ProgressFeed events={events} isRunning={isRunning} />
      )}

      {/* ── Final report ─────────────────────────────────────────────── */}
      {report && (
        <ReportPanel report={report} artifactId={artifactId} />
      )}
    </div>
  );
}
