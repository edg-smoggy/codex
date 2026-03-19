import type {
  ConversationSummary,
  HealthResponse,
  MessageItem,
  StreamMeta,
  StreamUsage,
  UsageDaily,
} from "./api";
import type { ApiKeyItem, DashboardStats, LogEntry, ModelConfig, SystemSettings } from "./view";

export interface StreamMessageParams {
  accessToken: string;
  message: string;
  model: string;
  signal?: AbortSignal;
  conversationId?: string;
  onMeta?: (data: StreamMeta) => void;
  onChunk: (delta: string) => void;
  onDone?: (usage: StreamUsage) => void;
}

export interface SendMessageParams {
  accessToken: string;
  message: string;
  model: string;
  signal?: AbortSignal;
  conversationId?: string;
}

export interface SendMessageResult {
  conversationId?: string;
  content: string;
  usage?: StreamUsage;
}

export interface ChatService {
  listConversations: (accessToken: string) => Promise<ConversationSummary[]>;
  listMessages: (accessToken: string, conversationId: string) => Promise<MessageItem[]>;
  streamMessage: (params: StreamMessageParams) => Promise<void>;
  sendMessage: (params: SendMessageParams) => Promise<SendMessageResult>;
  stopStream: (controller?: AbortController) => void;
  getUsage: (accessToken: string) => Promise<UsageDaily>;
  getHealth: (accessToken: string) => Promise<HealthResponse>;
}

export interface AdminService {
  getDashboardStats: (accessToken: string) => Promise<DashboardStats>;
  getModelsConfig: (baseModels?: Array<{ model: string; provider: string; enabled: boolean }>) => Promise<ModelConfig[]>;
  getApiKeys: () => Promise<ApiKeyItem[]>;
  getLogs: (
    accessToken: string,
    params?: { action?: string; limit?: number; offset?: number },
  ) => Promise<LogEntry[]>;
  getSettings: () => Promise<SystemSettings>;
}
