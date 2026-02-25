/**
 * renderWithProviders — wraps nodes in QueryClientProvider + MemoryRouter +
 * resets Zustand project store to a clean state.
 *
 * Use this in screen-level and hook-level tests to ensure isolated state
 * between test cases.
 */
import type { ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { useProjectStore } from "./stores/projectStore";

interface Options {
  initialPath?: string;
}

export function renderWithProviders(
  ui: ReactNode,
  { initialPath = "/" }: Options = {}
) {
  // Fresh QueryClient per test — avoids shared cache between tests
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
    },
  });

  // Reset Zustand project store to null state
  useProjectStore.setState({
    activeProjectId: null,
    activeProjectName: null,
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}
