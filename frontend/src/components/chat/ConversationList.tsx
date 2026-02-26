import { useRef, useState } from "react";
import { Trash2, Plus, MessageSquare } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "../../stores/chatStore";
import {
  useConversationList,
  useCreateConversation,
  useDeleteConversation,
  conversationKeys,
} from "../../hooks/useChat";
import { useUpdateNode } from "../../hooks/useNodes";
import { Spinner } from "../ui/Spinner";

interface ConversationListProps {
  projectId: string;
}

/**
 * ConversationList — left-hand panel listing all conversations for a project.
 *
 * - "+ New Chat" at top creates a new conversation and selects it.
 * - Active conversation is highlighted.
 * - Double-click the title to rename inline (persisted via PUT /nodes/{id}).
 * - Arrow keys move focus between list items; Enter or Space selects.
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
  const updateNode = useUpdateNode();

  // Inline title editing state
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  // Ref to the <ul> for arrow-key focus management
  const listRef = useRef<HTMLUListElement>(null);

  const handleNew = async () => {
    const conv = await createMutation.mutateAsync({ projectId });
    setActiveConv(conv.id);
  };

  const handleSelect = (id: string) => {
    if (editingConvId) return; // don't switch away while editing
    setActiveConv(id);
    queryClient.invalidateQueries({ queryKey: conversationKeys.detail(projectId, id) });
  };

  const handleDelete = (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    deleteMutation.mutate({ projectId, convId });
  };

  // ── Inline title editing ──────────────────────────────────────────────────

  const startEdit = (e: React.MouseEvent, convId: string, currentTitle: string) => {
    e.stopPropagation();
    e.preventDefault();
    setEditingConvId(convId);
    setEditingTitle(currentTitle);
  };

  const commitEdit = () => {
    if (!editingConvId) return;
    const trimmed = editingTitle.trim();
    if (trimmed) {
      updateNode.mutate({ id: editingConvId, payload: { title: trimmed } });
      // Optimistically refresh the conversation list
      queryClient.invalidateQueries({ queryKey: conversationKeys.list(projectId) });
    }
    setEditingConvId(null);
  };

  const cancelEdit = () => {
    setEditingConvId(null);
  };

  const handleEditKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") { e.preventDefault(); commitEdit(); }
    if (e.key === "Escape") { e.preventDefault(); cancelEdit(); }
  };

  // ── Arrow-key navigation ─────────────────────────────────────────────────

  const handleListKeyDown = (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const ul = listRef.current;
    if (!ul) return;
    const items = Array.from(ul.querySelectorAll<HTMLButtonElement>("button[data-conv-btn]"));
    if (!items.length) return;
    const focused = document.activeElement as HTMLButtonElement | null;
    const idx = focused ? items.indexOf(focused) : -1;
    let next: HTMLButtonElement | undefined;
    if (e.key === "ArrowDown") next = items[idx + 1] ?? items[0];
    if (e.key === "ArrowUp")   next = items[idx - 1] ?? items[items.length - 1];
    next?.focus();
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
      <ul
        ref={listRef}
        className="flex-1 overflow-y-auto py-1"
        role="list"
        onKeyDown={handleListKeyDown}
      >
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
            const isEditing = conv.id === editingConvId;
            return (
              <li key={conv.id}>
                <button
                  data-conv-btn
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

                  {isEditing ? (
                    /* Inline title editor */
                    <input
                      autoFocus
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={handleEditKeyDown}
                      onBlur={commitEdit}
                      onClick={(e) => e.stopPropagation()}
                      aria-label="Edit conversation title"
                      className="flex-1 min-w-0 rounded border border-blue-400 bg-white dark:bg-gray-800 px-1 py-0 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  ) : (
                    <span
                      className="flex-1 truncate"
                      onDoubleClick={(e) => startEdit(e, conv.id, conv.title)}
                      title="Double-click to rename"
                    >
                      {conv.title}
                    </span>
                  )}

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
