import { useState } from "react";
import { apiClient } from "../api/client";
import { useSettingsStore } from "../stores/settingsStore";
import type { ThemeValue, LLMProvider } from "../stores/settingsStore";

/**
 * Settings screen — appearance, LLM provider config, connection test.
 *
 * Settings are persisted client-side via Zustand + localStorage.
 * They are sent as extra params on applicable API calls where the backend
 * supports overrides (currently: model selection is server-side only;
 * tracked as a TODO for the backend).
 */
export function SettingsScreen() {
  const {
    theme, setTheme,
    llmProvider, setLLMProvider,
    ollamaBaseUrl, setOllamaBaseUrl,
    ollamaChatModel, setOllamaChatModel,
    ollamaEmbedModel, setOllamaEmbedModel,
    openaiApiKey, setOpenaiApiKey,
    openaiChatModel, setOpenaiChatModel,
  } = useSettingsStore();

  const [testStatus, setTestStatus] = useState<"idle" | "checking" | "ok" | "fail">("idle");
  const [showApiKey, setShowApiKey] = useState(false);

  const handleTestConnection = async () => {
    setTestStatus("checking");
    try {
      await apiClient.get("/nodes", { params: { limit: 1 } });
      setTestStatus("ok");
    } catch {
      setTestStatus("fail");
    }
  };

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "(same origin)";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto" data-testid="settings-screen">
      <div className="mx-auto w-full max-w-2xl space-y-8 p-6">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h1>

        {/* ── Appearance ─────────────────────────────────────────────── */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Appearance
          </h2>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
            <p className="mb-3 text-sm text-gray-700 dark:text-gray-300">Theme</p>
            <div className="flex gap-3">
              {(["light", "dark", "system"] as ThemeValue[]).map((t) => (
                <label
                  key={t}
                  className="flex cursor-pointer items-center gap-2"
                >
                  <input
                    type="radio"
                    name="theme"
                    value={t}
                    checked={theme === t}
                    onChange={() => setTheme(t)}
                    className="accent-blue-600"
                  />
                  <span className="text-sm capitalize text-gray-700 dark:text-gray-300">{t}</span>
                </label>
              ))}
            </div>
          </div>
        </section>

        {/* ── LLM Provider ───────────────────────────────────────────── */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            LLM Provider
          </h2>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-4">
            <div className="flex gap-6">
              {(["ollama", "openai"] as LLMProvider[]).map((p) => (
                <label key={p} className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="llmProvider"
                    value={p}
                    checked={llmProvider === p}
                    onChange={() => setLLMProvider(p)}
                    className="accent-blue-600"
                  />
                  <span className="text-sm capitalize text-gray-700 dark:text-gray-300">{p === "openai" ? "OpenAI" : "Ollama (local)"}</span>
                </label>
              ))}
            </div>

            {llmProvider === "ollama" && (
              <div className="space-y-3">
                <Field
                  label="Ollama Base URL"
                  value={ollamaBaseUrl}
                  onChange={setOllamaBaseUrl}
                  placeholder="http://localhost:11434"
                />
                <Field
                  label="Chat Model"
                  value={ollamaChatModel}
                  onChange={setOllamaChatModel}
                  placeholder="ministral-3:8b"
                />
                <Field
                  label="Embedding Model"
                  value={ollamaEmbedModel}
                  onChange={setOllamaEmbedModel}
                  placeholder="embeddinggemma:latest"
                />
              </div>
            )}

            {llmProvider === "openai" && (
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                    API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value={openaiApiKey}
                      onChange={(e) => setOpenaiApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="flex-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey((v) => !v)}
                      className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      {showApiKey ? "Hide" : "Show"}
                    </button>
                  </div>
                </div>
                <Field
                  label="Chat Model"
                  value={openaiChatModel}
                  onChange={setOpenaiChatModel}
                  placeholder="gpt-4o"
                />
              </div>
            )}

            <p className="text-xs text-gray-400 dark:text-gray-500">
              Note: these settings are stored locally in your browser. To change the active
              backend model, restart the server with matching environment variables.
              {/* TODO: expose /settings PUT endpoint on the backend */}
            </p>
          </div>
        </section>

        {/* ── Connection ─────────────────────────────────────────────── */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Connection
          </h2>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 dark:text-gray-400">API base URL:</span>
              <code className="rounded bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-700 dark:text-gray-300">
                {apiBase}
              </code>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testStatus === "checking"}
                className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {testStatus === "checking" ? "Testing…" : "Test Connection"}
              </button>
              {testStatus === "ok" && (
                <span className="text-xs text-green-600">✓ Connected</span>
              )}
              {testStatus === "fail" && (
                <span className="text-xs text-red-600">✗ Could not reach backend</span>
              )}
            </div>
          </div>
        </section>

        {/* ── About ──────────────────────────────────────────────────── */}
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            About
          </h2>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-1">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              <strong>Re:Search</strong> — AI researcher agent with knowledge graph
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Frontend v0.1.0 · React 18 + Vite 5 + TanStack Query v5
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

// ── Helper component ───────────────────────────────────────────────────────

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}
