import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ChatMessage } from "../types";

interface Citation {
  id: string;
  title: string;
  url?: string;
}

interface ChatStore {
  // Active conversation selection (persisted to sessionStorage — resets on new sessions)
  activeConvId: string | null;
  setActiveConv: (id: string | null) => void;

  // Optimistic in-memory messages for the active conversation
  // (supplements persisted messages from server)
  localMessages: ChatMessage[];
  addLocalMessage: (msg: ChatMessage) => void;
  clearLocalMessages: () => void;

  // Streaming state
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;

  // In-progress assistant reply (assembled token by token)
  streamingContent: string;
  appendStreamingContent: (text: string) => void;
  resetStreamingContent: () => void;

  // Citations from the last assistant reply
  citations: Citation[];
  setCitations: (c: Citation[]) => void;
}

/**
 * Zustand store for the active chat conversation and in-memory streaming state.
 *
 * `activeConvId` is persisted to `sessionStorage` so it survives page
 * refreshes within the same browser tab but resets on new sessions.
 * All streaming / local-message state is intentionally ephemeral (not persisted).
 */
export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      activeConvId: null,
      setActiveConv: (id) => set({ activeConvId: id }),

      localMessages: [],
      addLocalMessage: (msg) =>
        set((state) => ({ localMessages: [...state.localMessages, msg] })),
      clearLocalMessages: () => set({ localMessages: [] }),

      isStreaming: false,
      setIsStreaming: (v) => set({ isStreaming: v }),

      streamingContent: "",
      appendStreamingContent: (text) =>
        set((state) => ({ streamingContent: state.streamingContent + text })),
      resetStreamingContent: () => set({ streamingContent: "" }),

      citations: [],
      setCitations: (c) => set({ citations: c }),
    }),
    {
      name: "researchActiveConv",
      storage: createJSONStorage(() => sessionStorage),
      // Only persist the active conversation id; all other state is ephemeral
      partialize: (state) => ({ activeConvId: state.activeConvId }),
    }
  )
);
