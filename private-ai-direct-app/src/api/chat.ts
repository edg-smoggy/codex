import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

import type {
  AppConfigSummary,
  ConversationSummary,
  MessageItem,
  ModelInfo,
  StreamMeta,
  StreamUsage,
  ThinkingMode,
} from "../types/api";

interface StreamEnvelopeMeta extends StreamMeta {
  request_id: string;
}

interface StreamEnvelopeChunk {
  request_id: string;
  delta: string;
}

interface StreamEnvelopeDone {
  request_id: string;
  usage: StreamUsage;
}

interface StreamEnvelopeError {
  request_id: string;
  detail: string;
}

interface StreamMessageParams {
  requestId: string;
  message: string;
  model: string;
  thinkingMode?: ThinkingMode;
  regenerateAssistantId?: string;
  conversationId?: string;
  onMeta?: (data: StreamMeta) => void;
  onChunk: (delta: string) => void;
  onDone?: (usage: StreamUsage) => void;
}

export async function loadAppConfig(): Promise<AppConfigSummary> {
  return invoke<AppConfigSummary>("load_app_config");
}

export async function listModels(): Promise<ModelInfo[]> {
  return invoke<ModelInfo[]>("list_models");
}

export async function listConversations(): Promise<ConversationSummary[]> {
  return invoke<ConversationSummary[]>("list_conversations");
}

export async function listMessages(conversationId: string): Promise<MessageItem[]> {
  return invoke<MessageItem[]>("get_conversation_messages", { conversationId });
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await invoke("delete_conversation", { conversationId });
}

export async function streamChat(params: StreamMessageParams): Promise<void> {
  const offMeta = await listen<StreamEnvelopeMeta>("chat://meta", (event) => {
    if (event.payload.request_id !== params.requestId) return;
    params.onMeta?.({
      conversation_id: event.payload.conversation_id,
      assistant_message_id: event.payload.assistant_message_id,
      model: event.payload.model,
      provider: event.payload.provider,
    });
  });

  const offChunk = await listen<StreamEnvelopeChunk>("chat://chunk", (event) => {
    if (event.payload.request_id !== params.requestId) return;
    params.onChunk(event.payload.delta || "");
  });

  const result = await new Promise<void>(async (resolve, reject) => {
    const offDone = await listen<StreamEnvelopeDone>("chat://done", (event) => {
      if (event.payload.request_id !== params.requestId) return;
      params.onDone?.(event.payload.usage);
      void cleanup().then(() => resolve());
    });

    const offError = await listen<StreamEnvelopeError>("chat://error", (event) => {
      if (event.payload.request_id !== params.requestId) return;
      void cleanup().then(() => reject(new Error(event.payload.detail || "聊天失败")));
    });

    async function cleanup() {
      await Promise.all([offMeta(), offChunk(), offDone(), offError()]);
    }

    try {
      await invoke("start_chat_stream", {
        request: {
          requestId: params.requestId,
          conversationId: params.conversationId,
          message: params.message,
          model: params.model,
          thinkingMode: params.thinkingMode || "standard",
          regenerateAssistantId: params.regenerateAssistantId,
        },
      });
    } catch (error) {
      await cleanup();
      reject(error instanceof Error ? error : new Error("聊天失败"));
    }
  });

  return result;
}

export async function stopStream(requestId?: string): Promise<void> {
  if (!requestId) return;
  await invoke("stop_chat_stream", { requestId });
}
