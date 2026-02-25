import { useState, useRef, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GoalForm } from "../components/agent/GoalForm";
import { ProgressFeed } from "../components/agent/ProgressFeed";
import { ReportPanel } from "../components/agent/ReportPanel";
import { streamResearch } from "../api/agent";
import { linkNodeToProject } from "../api/projects";
import { useProjectStore } from "../stores/projectStore";
import { useAgentHistoryStore } from "../stores/agentHistoryStore";
import type { ResearchDepth, SseEvent, SseNodeEvent, SseDoneEvent } from "../types";

type ScreenTab = "run" | "history";

/**
 * AgentScreen â€” streaming research runner + history of past runs.
 */
export function AgentScreen() {
  const [screenTab, setScreenTab] = useState<ScreenTab>("run");
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<SseNodeEvent[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  // track goal+depth for history saving
  const lastGoalRef = useRef<{ goal: string; depth: string }>({ goal: "", depth: "" });

  const { activeProjectId } = useProjectStore();
  const queryClient = useQueryClient();
  const { runs, addRun, clearHistory } = useAgentHistoryStore();

  // Abort stream on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const handleSubmit = (goal: string, depth: ResearchDepth) => {
    lastGoalRef.current = { goal, depth };
    // Reset previous run state
    setEvents([]);
    setReport(null);
    setArtifactId(null);
    setError(null);
    setIsRunning(true);

    const abort = streamResearch(
      goal,
      depth,
      (e: SseEvent) => {
        if (e.event === "node") {
          setEvents((prev) => [...prev, e as SseNodeEvent]);
        } else if (e.event === "done") {
          const done = e as SseDoneEvent;
          setReport(done.report);
          setArtifactId(done.artifact_id);
          // Save to history
          addRun({
            id: done.artifact_id ?? crypto.randomUUID(),
            goal,
            depth,
            report: done.report,
            artifactId: done.artifact_id,
            completedAt: Date.now(),
          });
          if (activeProjectId) {
            linkNodeToProject(activeProjectId, done.artifact_id, "HAS_ARTIFACT")
              .then(() => {
                queryClient.invalidateQueries({ queryKey: ["projectGraph", activeProjectId] });
                queryClient.invalidateQueries({ queryKey: ["projectNodes", activeProjectId] });
              })
              .catch(() => {});
          }
        }
      },
      () => { setIsRunning(false); },
      (err: Error) => {
        setError(err.message);
        setIsRunning(false);
      }
    );

    abortRef.current = abort;
  };

  return (
    <div
      className="flex flex-1 flex-col overflow-hidden"
      data-testid="agent-screen"
    >
      {/* â”€â”€ Screen tab bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="flex shrink-0 gap-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-6 pt-4">
        <h1 className="mr-4 text-lg font-semibold text-gray-800 dark:text-gray-100 self-end pb-2">
          Agent Research
        </h1>
        {(["run", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setScreenTab(t)}
            className={`pb-2 text-sm font-medium capitalize transition-colors ${
              screenTab === t
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
            data-testid={`agent-tab-${t}`}
          >
            {t}
            {t === "history" && runs.length > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-xs text-gray-500">
                {runs.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* â”€â”€ Run tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {screenTab === "run" && (
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-6">
          {!activeProjectId && (
            <div
              role="status"
              data-testid="no-project-banner"
              className="rounded border border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-700 px-4 py-3 text-sm text-yellow-800 dark:text-yellow-300"
            >
              Select a project first. The research report won't be linked until a project is active.
            </div>
          )}

          <GoalForm onSubmit={handleSubmit} isRunning={isRunning} />

          {error && (
            <div
              role="alert"
              data-testid="error-banner"
              className="rounded border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-700 px-4 py-3 text-sm text-red-700 dark:text-red-400"
            >
              {error}
            </div>
          )}

          {events.length > 0 && (
            <ProgressFeed events={events} isRunning={isRunning} />
          )}

          {report && (
            <ReportPanel report={report} artifactId={artifactId} />
          )}
        </div>
      )}

      {/* â”€â”€ History tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {screenTab === "history" && (
        <div className="flex flex-1 flex-col overflow-y-auto p-6 gap-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {runs.length === 0 ? "No research runs yet." : `${runs.length} completed run${runs.length > 1 ? "s" : ""}`}
            </p>
            {runs.length > 0 && (
              <button
                onClick={() => {
                  if (window.confirm("Clear all history?")) clearHistory();
                }}
                className="text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400"
              >
                Clear history
              </button>
            )}
          </div>

          {runs.map((run) => (
            <div
              key={run.id}
              className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden"
            >
              {/* Run header */}
              <button
                onClick={() =>
                  setExpandedRunId((prev) => (prev === run.id ? null : run.id))
                }
                className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                    {run.goal}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {new Date(run.completedAt).toLocaleString()} Â· depth {run.depth}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {run.artifactId && (
                    <Link
                      to={`/map?node=${run.artifactId}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                    >
                      View in map â†’
                    </Link>
                  )}
                  <span className="text-xs text-gray-400">
                    {expandedRunId === run.id ? "â–²" : "â–¼"}
                  </span>
                </div>
              </button>

              {/* Expandable report */}
              {expandedRunId === run.id && (
                <div className="border-t border-gray-100 dark:border-gray-800 px-4 py-3 prose prose-sm dark:prose-invert max-w-none max-h-96 overflow-y-auto">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {run.report}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * AgentScreen â€” streaming research runner.
 *
 * - GoalForm submits a goal + depth to the agent.
 * - ProgressFeed shows live SSE node events during the run.
 * - ReportPanel renders the final markdown report.
 * - On completion, the artifact is linked to the active project (fire-and-forget).
 * - useEffect cleanup aborts any in-flight SSE stream on unmount.
 */
