export type UserRole = "admin" | "member";
export type UserStatus = "active" | "blocked";
export type ThinkingMode = "standard" | "thinking";

export interface UserInfo {
  id: string;
  username: string;
  role: UserRole;
  status: UserStatus;
  daily_token_limit: number;
  daily_cost_limit: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthBundle {
  user: UserInfo;
  token: TokenResponse;
}

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

export interface UsageDaily {
  usage_date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost: number;
  daily_token_limit: number;
  daily_cost_limit: number;
}

export interface AdminUserItem {
  id: string;
  username: string;
  role: UserRole;
  status: UserStatus;
  daily_token_limit: number;
  daily_cost_limit: number;
  created_at: string;
}

export interface AdminUsageItem {
  user_id: string;
  username: string;
  usage_date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost: number;
}

export interface HealthResponse {
  api: string;
  db: string;
  redis: string;
}

export interface StreamUsage {
  input_tokens: number;
  output_tokens: number;
  cost: number;
  daily_total_tokens: number;
  daily_total_cost: number;
}

export interface StreamMeta {
  conversation_id: string;
  assistant_message_id: string;
  model: string;
  provider: string;
}
