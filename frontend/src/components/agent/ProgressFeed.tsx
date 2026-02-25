import type { SseNodeEvent } from "../../types";

interface ProgressFeedProps {
  events: SseNodeEvent[];
  isRunning: boolean;
}

const KNOWN_NODES = ["planner", "searcher", "scraper", "synthesiser"];

function statusIcon(status: string, isLast: boolean, isRunning: boolean) {
  if (isLast && isRunning) return "⏳";
  if (status === "error") return "❌";
  return "✅";
}

/**
 * ProgressFeed — ordered list of agent node events received during a run.
 *
 * Known pipeline nodes are rendered in canonical order; unlisted nodes render
 * in the order they were received.  The last node shows ⏳ while `isRunning`.
 */
export function ProgressFeed({ events, isRunning }: ProgressFeedProps) {
  if (events.length === 0) return null;

  // Deduplicate: keep the last event per node name (final status wins)
  const seen = new Map<string, SseNodeEvent>();
  for (const ev of events) {
    seen.set(ev.node, ev);
  }

  // Order: known first (in canonical order), then any unlisted nodes
  const ordered: SseNodeEvent[] = [];
  for (const name of KNOWN_NODES) {
    if (seen.has(name)) ordered.push(seen.get(name)!);
  }
  for (const [name, ev] of seen.entries()) {
    if (!KNOWN_NODES.includes(name)) ordered.push(ev);
  }

  return (
    <div
      data-testid="progress-feed"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Progress</h3>
      <ol className="flex flex-col gap-2" aria-label="Agent progress steps">
        {ordered.map((ev, idx) => {
          const isLast = idx === ordered.length - 1;
          const icon = statusIcon(ev.status, isLast, isRunning);
          return (
            <li
              key={ev.node}
              data-testid={`progress-row-${ev.node}`}
              className="flex items-center gap-2 text-sm text-gray-700"
            >
              <span aria-label={icon} className="text-base leading-none">
                {icon}
              </span>
              <span className="font-medium capitalize">{ev.node}</span>
              <span className="ml-auto text-xs text-gray-400">{ev.status}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
