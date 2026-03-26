export type ThinkingMode = "standard" | "thinking";

export interface ModelInfo {
  model: string;
  provider: string;
  enabled: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  created_at: string;
}

export interface StreamUsage {
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

export interface StreamMeta {
  conversation_id: string;
  assistant_message_id: string;
  model: string;
  provider: string;
}

export interface ProviderStatus {
  provider: string;
  enabled: boolean;
  models: string[];
  config_path: string;
}

export interface AppConfigSummary {
  data_dir: string;
  config_path: string;
  providers: ProviderStatus[];
}
