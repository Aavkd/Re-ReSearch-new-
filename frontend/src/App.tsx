import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AppShell } from "./components/layout/AppShell";
import { ErrorBoundary } from "./components/layout/ErrorBoundary";
import { LibraryScreen } from "./screens/LibraryScreen";
import { MapScreen } from "./screens/MapScreen";
import { DraftsScreen } from "./screens/DraftsScreen";
import { AgentScreen } from "./screens/AgentScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { useTheme } from "./hooks/useTheme";

const queryClient = new QueryClient();

function App() {
  useTheme();
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Navigate to="/library" replace />} />
            <Route
              path="library"
              element={
                <ErrorBoundary>
                  <LibraryScreen />
                </ErrorBoundary>
              }
            />
            <Route
              path="map"
              element={
                <ErrorBoundary>
                  <MapScreen />
                </ErrorBoundary>
              }
            />
            <Route
              path="drafts"
              element={
                <ErrorBoundary>
                  <DraftsScreen />
                </ErrorBoundary>
              }
            />
            <Route
              path="drafts/:nodeId"
              element={
                <ErrorBoundary>
                  <DraftsScreen />
                </ErrorBoundary>
              }
            />
            <Route
              path="agent"
              element={
                <ErrorBoundary>
                  <AgentScreen />
                </ErrorBoundary>
              }
            />
            <Route
              path="settings"
              element={
                <ErrorBoundary>
                  <SettingsScreen />
                </ErrorBoundary>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      <Toaster position="bottom-right" toastOptions={{ duration: 4000 }} />
    </QueryClientProvider>
  );
}

export default App;
