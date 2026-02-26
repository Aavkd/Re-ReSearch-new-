import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStore } from "../../stores/chatStore";
import type { ChatMessage } from "../../types";

interface MessageBubbleProps {
  message: ChatMessage;
  /** true only for the in-progress assistant bubble */
  isStreaming?: boolean;
}

/** Format a Unix timestamp as HH:mm */
function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * MessageBubble — renders one chat message.
 *
 * User messages: right-aligned, blue background, plain text.
 * Assistant messages: left-aligned, grey background, Markdown rendered.
 * Streaming assistant message: shows live streamingContent from the store,
 * with a blinking cursor appended while streaming.
 */
export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const streamingContent = useChatStore((s) => s.streamingContent);
  const isUser = message.role === "user";

  const content = isStreaming ? streamingContent : message.content;

  return (
    <div
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
      data-testid={isUser ? "user-bubble" : "assistant-bubble"}
    >
      <div
        className={[
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm",
          isUser
            ? "bg-blue-600 text-white rounded-br-sm user-bubble"
            : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-bl-sm assistant-bubble",
        ].join(" ")}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content + (isStreaming ? "▍" : "")}
            </ReactMarkdown>
          </div>
        )}
        <p
          className={`mt-1 text-[10px] ${
            isUser ? "text-blue-200 text-right" : "text-gray-400 text-left"
          }`}
        >
          {formatTime(message.ts)}
        </p>
      </div>
    </div>
  );
}
