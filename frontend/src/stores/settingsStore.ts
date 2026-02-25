import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeValue = "light" | "dark" | "system";
export type LLMProvider = "ollama" | "openai";

interface SettingsStore {
  // Appearance
  theme: ThemeValue;
  setTheme: (t: ThemeValue) => void;

  // LLM provider
  llmProvider: LLMProvider;
  setLLMProvider: (p: LLMProvider) => void;

  ollamaBaseUrl: string;
  setOllamaBaseUrl: (url: string) => void;

  ollamaChatModel: string;
  setOllamaChatModel: (m: string) => void;

  ollamaEmbedModel: string;
  setOllamaEmbedModel: (m: string) => void;

  openaiApiKey: string;
  setOpenaiApiKey: (k: string) => void;

  openaiChatModel: string;
  setOpenaiChatModel: (m: string) => void;
}

/**
 * Persistent settings store (localStorage key: "researchSettings").
 *
 * Covers appearance (theme) and LLM provider configuration.
 * Theme is applied to <html> by the useTheme hook.
 */
export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      theme: "system",
      setTheme: (t) => set({ theme: t }),

      llmProvider: "ollama",
      setLLMProvider: (p) => set({ llmProvider: p }),

      ollamaBaseUrl: "http://localhost:11434",
      setOllamaBaseUrl: (url) => set({ ollamaBaseUrl: url }),

      ollamaChatModel: "ministral-3:8b",
      setOllamaChatModel: (m) => set({ ollamaChatModel: m }),

      ollamaEmbedModel: "embeddinggemma:latest",
      setOllamaEmbedModel: (m) => set({ ollamaEmbedModel: m }),

      openaiApiKey: "",
      setOpenaiApiKey: (k) => set({ openaiApiKey: k }),

      openaiChatModel: "gpt-4o",
      setOpenaiChatModel: (m) => set({ openaiChatModel: m }),
    }),
    {
      name: "researchSettings",
      partialize: (state) => ({
        theme: state.theme,
        llmProvider: state.llmProvider,
        ollamaBaseUrl: state.ollamaBaseUrl,
        ollamaChatModel: state.ollamaChatModel,
        ollamaEmbedModel: state.ollamaEmbedModel,
        openaiApiKey: state.openaiApiKey,
        openaiChatModel: state.openaiChatModel,
      }),
    }
  )
);
