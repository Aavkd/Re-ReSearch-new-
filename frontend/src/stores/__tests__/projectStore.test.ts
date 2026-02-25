import { beforeEach, describe, expect, it } from "vitest";
import { act } from "react";
import { useProjectStore } from "../../stores/projectStore";

// Reset the store and clear localStorage before every test so tests are isolated
beforeEach(() => {
  localStorage.clear();
  // Reset store state back to initial values
  act(() => {
    useProjectStore.setState({
      activeProjectId: null,
      activeProjectName: null,
    });
  });
});

describe("useProjectStore", () => {
  it("initial state has null ids", () => {
    const state = useProjectStore.getState();
    expect(state.activeProjectId).toBeNull();
    expect(state.activeProjectName).toBeNull();
  });

  it("setActiveProject updates both fields", () => {
    act(() => {
      useProjectStore.getState().setActiveProject("proj-1", "My Project");
    });
    const state = useProjectStore.getState();
    expect(state.activeProjectId).toBe("proj-1");
    expect(state.activeProjectName).toBe("My Project");
  });

  it("persists to localStorage after setActiveProject", () => {
    act(() => {
      useProjectStore.getState().setActiveProject("proj-2", "Saved Project");
    });
    const raw = localStorage.getItem("researchActiveProject");
    expect(raw).not.toBeNull();
    const stored = JSON.parse(raw!);
    expect(stored.state.activeProjectId).toBe("proj-2");
    expect(stored.state.activeProjectName).toBe("Saved Project");
  });

  it("clearActiveProject resets both fields to null", () => {
    act(() => {
      useProjectStore.getState().setActiveProject("proj-3", "To be cleared");
    });
    act(() => {
      useProjectStore.getState().clearActiveProject();
    });
    const state = useProjectStore.getState();
    expect(state.activeProjectId).toBeNull();
    expect(state.activeProjectName).toBeNull();
  });
});
