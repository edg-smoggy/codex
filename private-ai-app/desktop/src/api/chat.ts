import type {
  ConversationSummary,
  HealthResponse,
  MessageItem,
  ModelInfo,
  StreamMeta,
  StreamUsage,
  UsageDaily,
} from "../types/api";
import type { ChatService, SendMessageParams, SendMessageResult, StreamMessageParams } from "../types/services";
import { API_BASE, parseResponse } from "./http";

export async function getModels(accessToken: string): Promise<ModelInfo[]> {
  const resp = await fetch(`${API_BASE}/models`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<ModelInfo[]>(resp);
}

export async function listConversations(accessToken: string): Promise<ConversationSummary[]> {
  const resp = await fetch(`${API_BASE}/conversations`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<ConversationSummary[]>(resp);
}

export async function listMessages(accessToken: string, conversationId: string): Promise<MessageItem[]> {
  const resp = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<MessageItem[]>(resp);
}

export async function deleteConversation(accessToken: string, conversationId: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  await parseResponse<{ status: string }>(resp);
}

export async function getUsage(accessToken: string): Promise<UsageDaily> {
  const resp = await fetch(`${API_BASE}/usage/me/daily`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<UsageDaily>(resp);
}

export async function getHealth(accessToken: string): Promise<HealthResponse> {
  const resp = await fetch(`${API_BASE}/health`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<HealthResponse>(resp);
}

function parseEventBlock(block: string): { event: string; data: string } | null {
  const lines = block
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return null;

  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!eventLine || !dataLine) return null;

  return {
    event: eventLine.replace("event:", "").trim(),
    data: dataLine.replace("data:", "").trim(),
  };
}

export async function streamChat(params: StreamMessageParams): Promise<void> {
  const resp = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${params.accessToken}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    signal: params.signal,
    body: JSON.stringify({
      model: params.model,
      message: params.message,
      conversation_id: params.conversationId,
      thinking_mode: params.thinkingMode || "standard",
      regenerate_assistant_id: params.regenerateAssistantId,
    }),
  });

  if (!resp.ok || !resp.body) {
    await parseResponse(resp);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let splitIdx = buffer.indexOf("\n\n");
    while (splitIdx >= 0) {
      const chunk = buffer.slice(0, splitIdx);
      buffer = buffer.slice(splitIdx + 2);

      const parsed = parseEventBlock(chunk);
      if (parsed) {
        const payload = JSON.parse(parsed.data);
        if (parsed.event === "meta") {
          params.onMeta?.(payload as StreamMeta);
        } else if (parsed.event === "chunk") {
          params.onChunk(payload.delta || "");
        } else if (parsed.event === "done") {
          params.onDone?.((payload.usage || payload) as StreamUsage);
        } else if (parsed.event === "error") {
          throw new Error(payload.detail || "Chat failed");
        }
      }

      splitIdx = buffer.indexOf("\n\n");
    }
  }
}

export async function sendMessage(params: SendMessageParams): Promise<SendMessageResult> {
  let content = "";
  let usage: StreamUsage | undefined;
  let conversationId: string | undefined = params.conversationId;

  await streamChat({
    ...params,
    onMeta: (meta) => {
      conversationId = meta.conversation_id;
    },
    onChunk: (delta) => {
      content += delta;
    },
    onDone: (doneUsage) => {
      usage = doneUsage;
    },
  });

  return {
    conversationId,
    content,
    usage,
  };
}

export function stopStream(controller?: AbortController): void {
  controller?.abort();
}

export const chatService: ChatService = {
  listConversations,
  listMessages,
  deleteConversation,
  streamMessage: streamChat,
  sendMessage,
  stopStream,
  getUsage,
  getHealth,
};
