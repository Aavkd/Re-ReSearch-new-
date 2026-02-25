import { useState, useEffect, useRef } from "react";
import type { SearchMode } from "../../types";

export interface SearchBarProps {
  /** Called after the 300 ms debounce with the current query and mode. */
  onChange: (params: { query: string; mode: SearchMode }) => void;
}

/**
 * Search input with a mode selector (fuzzy / hybrid / semantic).
 *
 * The `query` value is debounced 300 ms before being propagated via
 * `onChange` to avoid firing a request on every keystroke.
 */
export function SearchBar({ onChange }: SearchBarProps) {
  const [inputValue, setInputValue] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");

  // Keep a stable reference to onChange to use in the effect without
  // re-triggering on every parent re-render.
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    const timer = setTimeout(() => {
      onChangeRef.current({ query: inputValue, mode });
    }, 300);
    return () => clearTimeout(timer);
  }, [inputValue, mode]);

  return (
    <div className="space-y-2" data-testid="search-bar">
      <div className="flex gap-2">
        <input
          type="search"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Search knowledge base…"
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          aria-label="Search query"
          data-testid="search-input"
        />
      </div>

      {/* Mode radio group */}
      <div className="flex gap-4" role="radiogroup" aria-label="Search mode">
        {(["fuzzy", "hybrid", "semantic"] as const).map((m) => (
          <label
            key={m}
            className="flex cursor-pointer items-center gap-1.5 text-sm text-gray-600"
          >
            <input
              type="radio"
              name="search-mode"
              value={m}
              checked={mode === m}
              onChange={() => setMode(m)}
              className="accent-blue-600"
            />
            {m.charAt(0).toUpperCase() + m.slice(1)}
          </label>
        ))}
      </div>
    </div>
  );
}
