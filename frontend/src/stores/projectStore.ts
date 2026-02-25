import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ProjectStore {
  activeProjectId: string | null;
  activeProjectName: string | null;
  setActiveProject: (id: string, name: string) => void;
  clearActiveProject: () => void;
}

/**
 * Zustand store for the currently-active project.
 *
 * Persisted to `localStorage` under the key `researchActiveProject` so the
 * selected project survives page refreshes.  Only `activeProjectId` and
 * `activeProjectName` are persisted; action functions are excluded by
 * Zustand's partialise default.
 */
export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      activeProjectId: null,
      activeProjectName: null,
      setActiveProject: (id, name) =>
        set({ activeProjectId: id, activeProjectName: name }),
      clearActiveProject: () =>
        set({ activeProjectId: null, activeProjectName: null }),
    }),
    {
      name: "researchActiveProject",
      // Only persist the data fields, not the action functions
      partialize: (state) => ({
        activeProjectId: state.activeProjectId,
        activeProjectName: state.activeProjectName,
      }),
    }
  )
);
