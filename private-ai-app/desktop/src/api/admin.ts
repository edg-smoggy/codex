import type { AdminUsageItem, AdminUserItem, ModelInfo } from "../types/api";
import type { AdminService } from "../types/services";
import type { ApiKeyItem, DashboardStats, LogEntry, ModelConfig, SystemSettings } from "../types/view";
import {
  MOCK_API_KEYS,
  MOCK_MODEL_CONFIGS,
  MOCK_SETTINGS,
} from "../mocks/adminMock";
import { API_BASE, DATA_SOURCE_MODE, parseResponse } from "./http";

type MockDomain = "keys" | "settings" | "model-manager";

function shouldUseMock(domain: MockDomain): boolean {
  if (DATA_SOURCE_MODE === "mock") return true;
  if (DATA_SOURCE_MODE === "real") return false;
  return domain === "keys" || domain === "settings" || domain === "model-manager";
}

function assertRealEndpoint(domain: MockDomain): void {
  if (!shouldUseMock(domain)) {
    throw new Error(`VITE_DATA_SOURCE_MODE=real requires backend endpoint for ${domain}`);
  }
}

export async function adminListUsers(accessToken: string): Promise<AdminUserItem[]> {
  const resp = await fetch(`${API_BASE}/admin/users`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<AdminUserItem[]>(resp);
}

export async function adminDailyUsage(accessToken: string): Promise<AdminUsageItem[]> {
  const resp = await fetch(`${API_BASE}/admin/usage/daily`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<AdminUsageItem[]>(resp);
}

export async function adminBlockUser(
  accessToken: string,
  userId: string,
  blocked: boolean,
): Promise<{ status: string }> {
  const resp = await fetch(`${API_BASE}/admin/users/${userId}/block`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ blocked }),
  });
  return parseResponse<{ status: string }>(resp);
}

export async function getDashboardStats(accessToken: string): Promise<DashboardStats> {
  const resp = await fetch(`${API_BASE}/admin/dashboard`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<DashboardStats>(resp);
}

export async function getModelsConfig(baseModels?: ModelInfo[]): Promise<ModelConfig[]> {
  if (!baseModels || baseModels.length === 0) {
    return structuredClone(MOCK_MODEL_CONFIGS);
  }

  const mockMap = shouldUseMock("model-manager") ? new Map(MOCK_MODEL_CONFIGS.map((item) => [item.id, item])) : new Map();

  return baseModels.map((model, index) => {
    const mock = mockMap.get(model.model);
    if (mock) {
      return {
        ...mock,
        enabled: model.enabled,
      };
    }

    return {
      id: model.model,
      name: model.model,
      provider: model.provider,
      icon: model.provider === "gemini" ? "🔵" : model.provider === "kimi" ? "🌙" : "✨",
      bg: "linear-gradient(135deg,#6c5ce7,#a29bfe)",
      calls: 80 + index * 17,
      cost: Number((0.2 + index * 0.13).toFixed(2)),
      usagePct: Math.min(100, 12 + index * 7),
      enabled: model.enabled,
    };
  });
}

export async function getApiKeys(): Promise<ApiKeyItem[]> {
  assertRealEndpoint("keys");
  return structuredClone(MOCK_API_KEYS);
}

interface GetLogsParams {
  action?: string;
  limit?: number;
  offset?: number;
}

export async function getLogs(accessToken: string, params: GetLogsParams = {}): Promise<LogEntry[]> {
  const query = new URLSearchParams();
  if (params.action) query.set("action", params.action);
  query.set("limit", String(params.limit ?? 50));
  query.set("offset", String(params.offset ?? 0));
  const suffix = query.toString();

  const resp = await fetch(`${API_BASE}/admin/logs${suffix ? `?${suffix}` : ""}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<LogEntry[]>(resp);
}

export async function getSettings(): Promise<SystemSettings> {
  assertRealEndpoint("settings");
  return structuredClone(MOCK_SETTINGS);
}

export const adminService: AdminService = {
  getDashboardStats,
  getModelsConfig,
  getApiKeys,
  getLogs,
  getSettings,
};
