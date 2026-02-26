import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  listConversations,
  createConversation,
  deleteConversation,
} from "../api/chat";
import { useChatStore } from "../stores/chatStore";
import type { ChatConversation } from "../types";

// ---------------------------------------------------------------------------
// Query key helpers
// ---------------------------------------------------------------------------

export const conversationKeys = {
  list: (projectId: string) => ["conversations", projectId] as const,
  detail: (projectId: string, convId: string) =>
    ["conversation", projectId, convId] as const,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Fetches all conversations for the given project.
 * Only enabled when `projectId` is non-null / non-empty.
 */
export function useConversationList(projectId: string | null) {
  return useQuery<ChatConversation[]>({
    queryKey: conversationKeys.list(projectId ?? ""),
    queryFn: () => listConversations(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------

interface CreateConversationVars {
  projectId: string;
  title?: string;
}

/**
 * Mutation to create a new conversation.
 * Invalidates the `['conversations', projectId]` query on success.
 */
export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation<ChatConversation, Error, CreateConversationVars>({
    mutationFn: ({ projectId, title }) => createConversation(projectId, title),
    onSuccess: (_data, { projectId }) => {
      queryClient.invalidateQueries({
        queryKey: conversationKeys.list(projectId),
      });
    },
  });
}

// ---------------------------------------------------------------------------

interface DeleteConversationVars {
  projectId: string;
  convId: string;
}

/**
 * Mutation to delete a conversation.
 * Invalidates the `['conversations', projectId]` query on success.
 * If the deleted conversation was active, clears the active selection.
 */
export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const { activeConvId, setActiveConv } = useChatStore();
  return useMutation<void, Error, DeleteConversationVars>({
    mutationFn: ({ projectId, convId }) => deleteConversation(projectId, convId),
    onSuccess: (_data, { projectId, convId }) => {
      queryClient.invalidateQueries({
        queryKey: conversationKeys.list(projectId),
      });
      if (activeConvId === convId) {
        setActiveConv(null);
      }
    },
  });
}
