import { Trash2, Plus, MessageSquare } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "../../stores/chatStore";
import {
  useConversationList,
  useCreateConversation,
  useDeleteConversation,
  conversationKeys,
} from "../../hooks/useChat";
import { Spinner } from "../ui/Spinner";

interface ConversationListProps {
  projectId: string;
}

/**
 * ConversationList — left-hand panel listing all conversations for a project.
 *
 * - "+ New Chat" at top creates a new conversation and selects it.
 * - Active conversation is highlighted.
 * - Trash icon on each row deletes (single-click, intentional).
 * - Loading skeleton of 3 ghost rows while fetching.
 * - "No conversations yet" empty state.
 */
export function ConversationList({ projectId }: ConversationListProps) {
  const queryClient = useQueryClient();

  const { activeConvId, setActiveConv } = useChatStore();

  const { data: conversations, isLoading } = useConversationList(projectId);
  const createMutation = useCreateConversation();
  const deleteMutation = useDeleteConversation();

  const handleNew = async () => {
    const conv = await createMutation.mutateAsync({ projectId });
    setActiveConv(conv.id);
  };

  const handleSelect = (id: string) => {
    setActiveConv(id);
    queryClient.invalidateQueries({ queryKey: conversationKeys.detail(projectId, id) });
  };

  const handleDelete = (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    deleteMutation.mutate({ projectId, convId });
  };

  return (
    <aside
      className="flex w-60 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
      aria-label="Conversations"
      data-testid="conversation-list"
    >
      {/* New Chat button */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={handleNew}
          disabled={createMutation.isPending}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          data-testid="new-chat-button"
        >
          <Plus size={14} aria-hidden="true" />
          New Chat
        </button>
      </div>

      {/* List */}
      <ul className="flex-1 overflow-y-auto py-1" role="list">
        {isLoading && (
          <>
            {[1, 2, 3].map((i) => (
              <li key={i} className="mx-2 my-1 h-9 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </>
        )}

        {!isLoading && (conversations ?? []).length === 0 && (
          <li className="px-3 py-6 text-center text-xs text-gray-400">
            No conversations yet
          </li>
        )}

        {!isLoading &&
          (conversations ?? []).map((conv) => {
            const isActive = conv.id === activeConvId;
            return (
              <li key={conv.id}>
                <button
                  onClick={() => handleSelect(conv.id)}
                  className={[
                    "group flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors",
                    isActive
                      ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
                  ].join(" ")}
                  aria-current={isActive ? "true" : undefined}
                  data-testid={`conv-item-${conv.id}`}
                >
                  <MessageSquare size={13} className="shrink-0 opacity-60" aria-hidden="true" />
                  <span className="flex-1 truncate">{conv.title}</span>
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label={`Delete conversation ${conv.title}`}
                    className="invisible ml-auto shrink-0 rounded p-0.5 text-gray-400 hover:text-red-500 group-hover:visible"
                    onClick={(e) => handleDelete(e, conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        deleteMutation.mutate({ projectId, convId: conv.id });
                      }
                    }}
                  >
                    {deleteMutation.isPending && deleteMutation.variables?.convId === conv.id ? (
                      <Spinner size="3" />
                    ) : (
                      <Trash2 size={13} aria-hidden="true" />
                    )}
                  </span>
                </button>
              </li>
            );
          })}
      </ul>
    </aside>
  );
}
