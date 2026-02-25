import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LibraryScreen } from "./screens/LibraryScreen";
import { MapScreen } from "./screens/MapScreen";
import { DraftsScreen } from "./screens/DraftsScreen";
import { AgentScreen } from "./screens/AgentScreen";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Navigate to="/library" replace />} />
            <Route path="library" element={<LibraryScreen />} />
            <Route path="map" element={<MapScreen />} />
            <Route path="drafts" element={<DraftsScreen />} />
            <Route path="drafts/:nodeId" element={<DraftsScreen />} />
            <Route path="agent" element={<AgentScreen />} />
          </Route>
        </Routes>
      </BrowserRouter>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

export default App;
