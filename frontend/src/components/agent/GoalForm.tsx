import { useState } from "react";
import type { ResearchDepth } from "../../types";

interface GoalFormProps {
  onSubmit: (goal: string, depth: ResearchDepth) => void;
  isRunning: boolean;
}

const DEPTH_OPTIONS: { value: ResearchDepth; label: string }[] = [
  { value: "quick", label: "Quick" },
  { value: "standard", label: "Standard" },
  { value: "deep", label: "Deep" },
];

/**
 * GoalForm — multi-line textarea + depth selector + submit button.
 *
 * - Disabled while `isRunning` is true.
 * - "Run Research" changes to "Running…" with a spinner while running.
 * - The goal textarea requires non-empty input before the button is enabled.
 */
export function GoalForm({ onSubmit, isRunning }: GoalFormProps) {
  const [goal, setGoal] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed) return;
    onSubmit(trimmed, depth);
  };

  return (
    <form
      data-testid="goal-form"
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
    >
      {/* ── Goal textarea ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-1">
        <label
          htmlFor="goal"
          className="text-sm font-medium text-gray-700"
        >
          Research goal
        </label>
        <textarea
          id="goal"
          name="goal"
          rows={3}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={isRunning}
          placeholder="What would you like to research?"
          className="resize-y rounded border border-gray-300 px-3 py-2 text-sm
                     placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500
                     disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
          data-testid="goal-textarea"
        />
      </div>

      {/* ── Depth selector ─────────────────────────────────────────────── */}
      <fieldset className="flex items-center gap-4">
        <legend className="text-sm font-medium text-gray-700 mr-2">
          Depth
        </legend>
        {DEPTH_OPTIONS.map(({ value, label }) => (
          <label key={value} className="flex items-center gap-1.5 text-sm text-gray-600">
            <input
              type="radio"
              name="depth"
              value={value}
              checked={depth === value}
              onChange={() => setDepth(value)}
              disabled={isRunning}
              className="accent-blue-600"
            />
            {label}
          </label>
        ))}
      </fieldset>

      {/* ── Submit button ──────────────────────────────────────────────── */}
      <button
        type="submit"
        disabled={isRunning || !goal.trim()}
        data-testid="run-button"
        className="flex items-center justify-center gap-2 rounded bg-blue-600 px-4 py-2
                   text-sm font-medium text-white transition-colors hover:bg-blue-700
                   disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isRunning ? (
          <>
            <span
              className="inline-block h-4 w-4 animate-spin rounded-full
                         border-2 border-white border-t-transparent"
              aria-hidden="true"
            />
            Running…
          </>
        ) : (
          "Run Research"
        )}
      </button>
    </form>
  );
}
