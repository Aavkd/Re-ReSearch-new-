import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AgentRun {
  id: string;
  goal: string;
  depth: string;
  report: string;
  artifactId: string | null;
  completedAt: number; // Unix ms
}

interface AgentHistoryStore {
  runs: AgentRun[];
  addRun: (run: AgentRun) => void;
  clearHistory: () => void;
}

const MAX_RUNS = 20;

/**
 * Persisted store for completed agent research runs.
 * Capped at MAX_RUNS most-recent entries.
 */
export const useAgentHistoryStore = create<AgentHistoryStore>()(
  persist(
    (set) => ({
      runs: [],
      addRun: (run) =>
        set((state) => ({
          runs: [run, ...state.runs].slice(0, MAX_RUNS),
        })),
      clearHistory: () => set({ runs: [] }),
    }),
    {
      name: "researchAgentHistory",
    }
  )
);
