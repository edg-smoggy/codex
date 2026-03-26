import { create } from "zustand";

import {
  deleteConversation as deleteConversationApi,
  listConversations,
  listMessages,
  listModels,
  loadAppConfig,
  stopStream,
  streamChat,
} from "../api/chat";
import type { AppConfigSummary, ConversationSummary, MessageItem, StreamUsage, ThinkingMode } from "../types/api";
import type { UIModel } from "../types/view";
import { toUIModel } from "../mocks/modelCatalog";

interface ChatStore {
  appConfig?: AppConfigSummary;
  models: UIModel[];
  selectedModelId: string;
  thinkingMode: ThinkingMode;
  conversations: ConversationSummary[];
  activeConversationId?: string;
  messages: MessageItem[];
  draftAssistant: string;
  input: string;
  streaming: boolean;
  error: string;
  activeRequestId?: string;

  setInput: (value: string) => void;
  clearError: () => void;
  setSelectedModel: (modelId: string) => void;
  setThinkingMode: (mode: ThinkingMode) => void;
  setActiveConversation: (conversationId?: string) => void;

  hydrateBase: () => Promise<void>;
  hydrateMessages: () => Promise<void>;
  startNewConversation: () => void;
  sendMessage: () => Promise<void>;
  regenerateLastAssistant: () => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  stopStreaming: () => Promise<void>;
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
    provider: "local",
    input_tokens: 0,
    output_tokens: 0,
    cost: 0,
    created_at: new Date().toISOString(),
  };
}

function updateAssistantUsage(message: MessageItem, usage?: StreamUsage): MessageItem {
  if (!usage) return message;
  return {
    ...message,
    input_tokens: usage.input_tokens,
    output_tokens: usage.output_tokens,
    cost: usage.cost,
  };
}

function supportsThinkingMode(model?: UIModel): boolean {
  if (!model) return false;
  return (
    model.model === "kimi-k2.5" ||
    model.model === "anthropic/claude-opus-4.6" ||
    model.model === "anthropic/claude-sonnet-4.6"
  );
}

function errorText(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) return err.message;
  if (typeof err === "string" && err.trim()) return err;
  if (typeof err === "object" && err && "message" in err) {
    const message = (err as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  appConfig: undefined,
  models: [],
  selectedModelId: "",
  thinkingMode: "standard",
  conversations: [],
  activeConversationId: undefined,
  messages: [],
  draftAssistant: "",
  input: "",
  streaming: false,
  error: "",
  activeRequestId: undefined,

  setInput: (value) => set({ input: value }),
  clearError: () => set({ error: "" }),
  setSelectedModel: (modelId) => set((state) => ({
    selectedModelId: modelId,
    thinkingMode: supportsThinkingMode(state.models.find((item) => item.model === modelId)) ? state.thinkingMode : "standard",
  })),
  setThinkingMode: (mode) => set({ thinkingMode: mode }),
  setActiveConversation: (conversationId) => set({ activeConversationId: conversationId }),

  hydrateBase: async () => {
    const [config, modelsResp, conversationsResp] = await Promise.all([loadAppConfig(), listModels(), listConversations()]);
    const enabledModels = modelsResp.filter((item) => item.enabled).map(toUIModel);
    const sortedConversations = byUpdatedAtDesc(conversationsResp);

    set((state) => {
      const selectedModelId =
        state.selectedModelId && enabledModels.some((item) => item.model === state.selectedModelId)
          ? state.selectedModelId
          : enabledModels[0]?.model || "";
      const selectedModel = enabledModels.find((item) => item.model === selectedModelId);
      const activeConversationId =
        state.activeConversationId && sortedConversations.some((item) => item.id === state.activeConversationId)
          ? state.activeConversationId
          : sortedConversations[0]?.id;

      return {
        appConfig: config,
        models: enabledModels,
        selectedModelId,
        thinkingMode: supportsThinkingMode(selectedModel) ? state.thinkingMode : "standard",
        activeConversationId,
        conversations: sortedConversations,
      };
    });
  },

  hydrateMessages: async () => {
    const conversationId = get().activeConversationId;
    if (!conversationId) {
      set({ messages: [] });
      return;
    }
    const items = await listMessages(conversationId);
    set({ messages: items });
  },

  startNewConversation: () => {
    set({ activeConversationId: undefined, messages: [], draftAssistant: "", error: "" });
  },

  sendMessage: async () => {
    const state = get();
    const text = state.input.trim();
    if (!text || !state.selectedModelId || state.streaming) return;

    const requestId = `req-${Date.now()}`;
    const provisionalConversationId = state.activeConversationId || `pending-${Date.now()}`;
    const localUser = buildLocalUserMessage(text, provisionalConversationId, state.selectedModelId);

    set((prev) => ({
      input: "",
      streaming: true,
      error: "",
      draftAssistant: "",
      activeRequestId: requestId,
      messages: [...prev.messages, localUser],
    }));

    let resolvedConversationId = state.activeConversationId;
    let resolvedAssistantId = `pending-assistant-${Date.now()}`;
    let doneUsage: StreamUsage | undefined;

    try {
      await streamChat({
        requestId,
        message: text,
        model: state.selectedModelId,
        conversationId: state.activeConversationId,
        thinkingMode: state.thinkingMode,
        onMeta: (meta) => {
          resolvedConversationId = meta.conversation_id;
          resolvedAssistantId = meta.assistant_message_id;
          set({ activeConversationId: meta.conversation_id });
        },
        onChunk: (delta) => {
          set((prev) => ({ draftAssistant: prev.draftAssistant + delta }));
        },
        onDone: (usage) => {
          doneUsage = usage;
        },
      });

      await get().hydrateBase();
      if (resolvedConversationId) {
        set({ activeConversationId: resolvedConversationId });
        await get().hydrateMessages();
      }
      set((prev) => ({
        streaming: false,
        draftAssistant: "",
        activeRequestId: undefined,
        messages: prev.messages.map((item) =>
          item.id === resolvedAssistantId ? updateAssistantUsage(item, doneUsage) : item,
        ),
      }));
    } catch (err) {
      set((prev) => ({
        streaming: false,
        activeRequestId: undefined,
        error: errorText(err, "发送失败"),
        draftAssistant: "",
        messages: prev.messages.filter((item) => item.id !== localUser.id),
      }));
      throw err;
    }
  },

  regenerateLastAssistant: async () => {
    const state = get();
    if (state.streaming || !state.activeConversationId) return;

    const assistantIndex = [...state.messages].reverse().findIndex((item) => item.role === "assistant");
    if (assistantIndex < 0) return;
    const targetAssistant = [...state.messages].reverse()[assistantIndex];
    const targetIdx = state.messages.findIndex((item) => item.id === targetAssistant.id);
    if (targetIdx <= 0) return;
    const previousUser = [...state.messages.slice(0, targetIdx)].reverse().find((item) => item.role === "user");
    if (!previousUser) return;

    const requestId = `req-${Date.now()}`;
    let doneUsage: StreamUsage | undefined;

    set({
      streaming: true,
      error: "",
      draftAssistant: "",
      activeRequestId: requestId,
    });

    try {
      await streamChat({
        requestId,
        message: previousUser.content,
        model: state.selectedModelId,
        conversationId: state.activeConversationId,
        thinkingMode: state.thinkingMode,
        regenerateAssistantId: targetAssistant.id,
        onChunk: (delta) => {
          set((prev) => ({ draftAssistant: prev.draftAssistant + delta }));
        },
        onDone: (usage) => {
          doneUsage = usage;
        },
      });

      await get().hydrateBase();
      await get().hydrateMessages();
      set((prev) => ({
        streaming: false,
        draftAssistant: "",
        activeRequestId: undefined,
        messages: prev.messages.map((item) =>
          item.id === targetAssistant.id ? updateAssistantUsage(item, doneUsage) : item,
        ),
      }));
    } catch (err) {
      set({
        streaming: false,
        activeRequestId: undefined,
        draftAssistant: "",
        error: errorText(err, "重新生成失败"),
      });
      throw err;
    }
  },

  deleteConversation: async (conversationId) => {
    await deleteConversationApi(conversationId);
    set((state) => {
      const nextConversations = state.conversations.filter((item) => item.id !== conversationId);
      const activeConversationId = state.activeConversationId === conversationId ? nextConversations[0]?.id : state.activeConversationId;
      return {
        conversations: nextConversations,
        activeConversationId,
        messages: activeConversationId ? state.messages : [],
      };
    });
    await get().hydrateBase();
    await get().hydrateMessages();
  },

  stopStreaming: async () => {
    await stopStream(get().activeRequestId);
  },
}));
