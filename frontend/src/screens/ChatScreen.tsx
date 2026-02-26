import { useEffect, useRef, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useProjectStore } from "../stores/projectStore";
import { useChatStore } from "../stores/chatStore";
import { streamChatMessage, getConversation } from "../api/chat";
import { conversationKeys } from "../hooks/useChat";
import { ConversationList } from "../components/chat/ConversationList";
import { MessageBubble } from "../components/chat/MessageBubble";
import { CitationList } from "../components/chat/CitationList";
import { ChatInput } from "../components/chat/ChatInput";
import { EmptyState } from "../components/ui/EmptyState";
import { Spinner } from "../components/ui/Spinner";
import type { ChatMessage, ChatSseEvent, ChatCitationEvent } from "../types";

/**
 * ChatScreen — project-scoped conversational chat grounded in the knowledge base.
 *
 * Layout:
 *   <ConversationList 240px> | <message panel>
 *
 * The message panel shows persisted messages fetched from the server
 * plus optimistic local messages appended on send.  While streaming the
 * in-progress reply is shown as a special streaming bubble assembled in
 * chatStore.streamingContent.
 */
export function ChatScreen() {
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const {
    activeConvId,
    localMessages,
    isStreaming,
    streamingContent,
    citations,
    addLocalMessage,
    clearLocalMessages,
    setIsStreaming,
    appendStreamingContent,
    resetStreamingContent,
    setCitations,
  } = useChatStore();

  const queryClient = useQueryClient();
  const abortRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Fetch the persisted conversation (messages from server)
  const {
    data: conversation,
    isLoading: convLoading,
  } = useQuery({
    queryKey: conversationKeys.detail(activeProjectId ?? "", activeConvId ?? ""),
    queryFn: () => getConversation(activeProjectId!, activeConvId!),
    enabled: !!activeProjectId && !!activeConvId,
    staleTime: 0,
  });

  // Clear local messages whenever the active conversation changes
  useEffect(() => {
    clearLocalMessages();
    resetStreamingContent();
    setCitations([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConvId]);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages, streamingContent]);

  // Abort SSE stream on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const handleSend = useCallback(
    (text: string) => {
      if (!activeProjectId || !activeConvId || isStreaming) return;

      const userMsg: ChatMessage = {
        role: "user",
        content: text,
        ts: Math.floor(Date.now() / 1000),
      };
      addLocalMessage(userMsg);
      setIsStreaming(true);
      resetStreamingContent();
      setCitations([]);

      // Build the history from persisted + local messages (exclude the one we just added)
      const history = [
        ...(conversation?.messages ?? []),
        ...localMessages,
      ].map(({ role, content }) => ({ role, content }));

      abortRef.current = streamChatMessage(
        activeProjectId,
        activeConvId,
        text,
        history,
        (e: ChatSseEvent) => {
          if (e.event === "token") {
            appendStreamingContent(e.text);
          } else if (e.event === "citation") {
            setCitations((e as ChatCitationEvent).nodes);
          }
        },
        () => {
          // done — assemble assistant message and finalise
          useChatStore.getState().addLocalMessage({
            role: "assistant",
            content: useChatStore.getState().streamingContent,
            ts: Math.floor(Date.now() / 1000),
          });
          resetStreamingContent();
          setIsStreaming(false);
          // Refresh server copy in the background
          queryClient.invalidateQueries({
            queryKey: conversationKeys.detail(activeProjectId, activeConvId),
          });
        },
        (err: Error) => {
          console.error("Chat stream error:", err);
          setIsStreaming(false);
          resetStreamingContent();
        }
      );
    },
    [
      activeProjectId,
      activeConvId,
      isStreaming,
      conversation,
      localMessages,
      addLocalMessage,
      appendStreamingContent,
      resetStreamingContent,
      setCitations,
      setIsStreaming,
      queryClient,
    ]
  );

  // ── Guards ──────────────────────────────────────────────────────────────────
  if (!activeProjectId) {
    return (
      <div className="flex flex-1 overflow-hidden" data-testid="chat-screen">
        <EmptyState message="Select a project to start chatting." />
      </div>
    );
  }

  // ── Main layout ─────────────────────────────────────────────────────────────
  const serverMessages: ChatMessage[] = conversation?.messages ?? [];

  // When server messages are loaded we still show local ones appended on top
  // so optimistic messages appear instantly.
  const displayMessages: ChatMessage[] =
    serverMessages.length > 0
      ? [...serverMessages, ...localMessages]
      : localMessages;

  return (
    <div className="flex flex-1 overflow-hidden" data-testid="chat-screen">
      {/* — Conversation list ——————————————————————————————————————————————— */}
      <ConversationList projectId={activeProjectId} />

      {/* — Chat panel ————————————————————————————————————————————————————— */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!activeConvId ? (
          <EmptyState message="Select or create a conversation." />
        ) : (
          <>
            {/* Message list */}
            <div
              className="flex-1 overflow-y-auto px-6 py-4 space-y-3"
              role="log"
              aria-live="polite"
              aria-label="Conversation messages"
              data-testid="message-list"
            >
              {convLoading && (
                <div className="flex justify-center py-8">
                  <Spinner size="6" />
                </div>
              )}

              {!convLoading &&
                displayMessages.map((msg, idx) => (
                  <MessageBubble
                    key={`${msg.ts}-${idx}`}
                    message={msg}
                    isStreaming={false}
                  />
                ))}

              {/* Streaming bubble */}
              {isStreaming && (
                <MessageBubble
                  message={{ role: "assistant", content: "", ts: Math.floor(Date.now() / 1000) }}
                  isStreaming={true}
                />
              )}

              {/* Auto-scroll sentinel */}
              <div ref={bottomRef} />
            </div>

            {/* Citations */}
            {citations.length > 0 && !isStreaming && (
              <div className="px-6 pb-2">
                <CitationList citations={citations} />
              </div>
            )}

            {/* Chat input */}
            <ChatInput onSend={handleSend} disabled={isStreaming} />
          </>
        )}
      </div>
    </div>
  );
}
