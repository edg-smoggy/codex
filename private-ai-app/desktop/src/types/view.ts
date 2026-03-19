import type { AdminUsageItem, AdminUserItem, ModelInfo } from "./api";

export type DataSourceMode = "real" | "mock" | "hybrid";

export interface ModelTag {
  label: string;
  kind: "fast" | "smart" | "creative" | "vision" | "new";
}

export interface UIModel extends ModelInfo {
  name: string;
  desc: string;
  icon: string;
  bgClass: string;
  color: string;
  category: string;
  tags: ModelTag[];
}

export interface ConversationVM {
  id: string;
  title: string;
  model: UIModel;
  updatedAt: string;
}

export interface DashboardStats {
  total_users: number;
  active_users_today: number;
  total_conversations: number;
  total_messages_today: number;
  total_cost_today: number;
  total_tokens_today: number;
  models_enabled: number;
  daily_usage_7d: Array<{ date: string; tokens: number; cost: number; requests: number }>;
}

export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  icon: string;
  bg: string;
  calls: number;
  cost: number;
  usagePct: number;
  enabled: boolean;
}

export interface ApiKeyItem {
  id: string;
  provider: string;
  maskedKey: string;
  status: "正常" | "余额不足" | "失效";
  color: string;
}

export interface LogEntry {
  id: string;
  user_id: string | null;
  username: string | null;
  action: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface SystemSettings {
  appName: string;
  description: string;
  domain: string;
  registrationMode: "invite" | "open" | "closed";
  inviteCode: string;
  defaultRole: "member" | "pro";
  maxUsers: number;
  sessionTimeoutMinutes: number;
  maxConcurrentSessions: number;
  rateLimitPerMinute: number;
}

export interface AdminHydratedData {
  users: AdminUserItem[];
  usage: AdminUsageItem[];
  models: ModelInfo[];
  dashboard: DashboardStats;
  modelConfigs: ModelConfig[];
  apiKeys: ApiKeyItem[];
  logs: LogEntry[];
  settings: SystemSettings;
}
