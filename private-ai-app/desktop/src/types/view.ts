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
  totalUsers: number;
  todayConversations: number;
  todayCost: number;
  availableModels: number;
  userDelta: string;
  convDelta: string;
  costDelta: string;
  modelDelta: string;
  trend: Array<{ label: string; value: number }>;
  modelDistribution: Array<{ label: string; value: number; color: string }>;
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
  type: "api" | "user" | "system" | "error";
  text: string;
  meta: string;
  time: string;
  color: string;
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
