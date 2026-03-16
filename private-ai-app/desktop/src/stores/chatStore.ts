import { create } from "zustand";

import { getHealth, getModels, getUsage, listConversations, listMessages, streamChat } from "../api/chat";
import { toUIModel } from "../mocks/modelCatalog";
import type { ConversationSummary, HealthResponse, MessageItem, StreamUsage, UsageDaily } from "../types/api";
import type { UIModel } from "../types/view";

interface ChatStore {
  models: UIModel[];
  selectedModelId: string;
  conversations: ConversationSummary[];
  activeConversationId?: string;
  messages: MessageItem[];
  usage?: UsageDaily;
  health?: HealthResponse;
  draftAssistant: string;
  input: string;
  streaming: boolean;
  error: string;
  streamAbort?: AbortController;

  setInput: (value: string) => void;
  clearError: () => void;
  setSelectedModel: (modelId: string) => void;
  setActiveConversation: (conversationId?: string) => void;

  hydrateBase: (runner: <T>(fn: (token: string) => Promise<T>) => Promise<T>) => Promise<void>;
  hydrateMessages: (runner: <T>(fn: (token: string) => Promise<T>) => Promise<T>) => Promise<void>;
  startNewConversation: () => void;
  sendMessage: (runner: <T>(fn: (token: string) => Promise<T>) => Promise<T>) => Promise<void>;
  stopStreaming: () => void;
}

function byUpdatedAtDesc(items: ConversationSummary[]): ConversationSummary[] {
  return [...items].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
}

function buildLocalUserMessage(content: string, conversationId: string, modelId: string): MessageItem {
  return {
    id: `local-user-${Date.now()}`,
    conversation_id: conversationId,
    role: "user",
    content,
    model: modelId,
    provider: "client",
    input_tokens: 0,
    output_tokens: 0,
    cost: 0,
    created_at: new Date().toISOString(),
  };
}

export const useChatStore = create<ChatStore>((set, get) => ({
  models: [],
  selectedModelId: "",
  conversations: [],
  activeConversationId: undefined,
  messages: [],
  usage: undefined,
  health: undefined,
  draftAssistant: "",
  input: "",
  streaming: false,
  error: "",
  streamAbort: undefined,

  setInput: (value) => set({ input: value }),
  clearError: () => set({ error: "" }),
  setSelectedModel: (modelId) => set({ selectedModelId: modelId }),
  setActiveConversation: (conversationId) => set({ activeConversationId: conversationId }),

  hydrateBase: async (runner) => {
    const [modelsResp, convResp, usageResp, healthResp] = await Promise.all([
      runner((token) => getModels(token)),
      runner((token) => listConversations(token)),
      runner((token) => getUsage(token)),
      runner((token) => getHealth(token)),
    ]);

    const enabledModels = modelsResp.filter((item) => item.enabled).map(toUIModel);
    const sortedConversations = byUpdatedAtDesc(convResp);

    set((state) => {
      const selectedModelId =
        state.selectedModelId && enabledModels.some((item) => item.model === state.selectedModelId)
          ? state.selectedModelId
          : enabledModels[0]?.model || "";

      const activeConversationId =
        state.activeConversationId && sortedConversations.some((item) => item.id === state.activeConversationId)
          ? state.activeConversationId
          : sortedConversations[0]?.id;

      return {
        models: enabledModels,
        selectedModelId,
        conversations: sortedConversations,
        activeConversationId,
        usage: usageResp,
        health: healthResp,
      };
    });
  },

  hydrateMessages: async (runner) => {
    const conversationId = get().activeConversationId;
    if (!conversationId) {
      set({ messages: [] });
      return;
    }

    const items = await runner((token) => listMessages(token, conversationId));
    set({ messages: items });
  },

  startNewConversation: () => {
    set({ activeConversationId: undefined, messages: [], draftAssistant: "", error: "" });
  },

  sendMessage: async (runner) => {
    const state = get();
    const text = state.input.trim();
    if (!text || !state.selectedModelId || state.streaming) {
      return;
    }

    const provisionalConversationId = state.activeConversationId || `pending-${Date.now()}`;
    const localUser = buildLocalUserMessage(text, provisionalConversationId, state.selectedModelId);

    const streamAbort = new AbortController();

    set((prev) => ({
      input: "",
      streaming: true,
      error: "",
      draftAssistant: "",
      streamAbort,
      messages: [...prev.messages, localUser],
    }));

    let resolvedConversationId = state.activeConversationId;
    let doneUsage: StreamUsage | undefined;

    try {
      await runner((token) =>
        streamChat({
          accessToken: token,
          message: text,
          model: state.selectedModelId,
          conversationId: state.activeConversationId,
          signal: streamAbort.signal,
          onMeta: (meta) => {
            resolvedConversationId = meta.conversation_id;
            set({ activeConversationId: meta.conversation_id });
          },
          onChunk: (delta) => {
            set((prev) => ({ draftAssistant: prev.draftAssistant + delta }));
          },
          onDone: (usage) => {
            doneUsage = usage;
          },
        }),
      );

      await get().hydrateBase(runner);

      const freshConversationId = resolvedConversationId || get().activeConversationId;
      if (freshConversationId) {
        set({ activeConversationId: freshConversationId });
        const freshMessages = await runner((token) => listMessages(token, freshConversationId));
        set({ messages: freshMessages });
      }

      const usageFromDone = doneUsage;
      if (usageFromDone && get().usage) {
        set((prev) => {
          if (!prev.usage) return {};
          return {
            usage: {
              ...prev.usage,
              total_tokens: usageFromDone.daily_total_tokens,
              total_cost: usageFromDone.daily_total_cost,
            },
          };
        });
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        set({ error: "已停止生成" });
      } else {
        set({ error: err instanceof Error ? err.message : "发送失败" });
      }
    } finally {
      set({
        draftAssistant: "",
        streaming: false,
        streamAbort: undefined,
      });
    }
  },

  stopStreaming: () => {
    get().streamAbort?.abort();
  },
}));
