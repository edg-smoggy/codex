import { create } from "zustand";

import type { AdminUsageItem, AdminUserItem, ModelInfo } from "../types/api";
import type { ApiKeyItem, DashboardStats, LogEntry, ModelConfig, SystemSettings } from "../types/view";
import {
  adminBlockUser,
  adminDailyUsage,
  adminListUsers,
  getApiKeys,
  getDashboardStats,
  getLogs,
  getModelsConfig,
  getSettings,
} from "../api/admin";
import { getModels } from "../api/chat";

export type AdminSection = "dashboard" | "users" | "models" | "keys" | "logs" | "settings";

interface AdminStore {
  section: AdminSection;
  users: AdminUserItem[];
  usage: AdminUsageItem[];
  models: ModelInfo[];
  dashboard?: DashboardStats;
  modelConfigs: ModelConfig[];
  apiKeys: ApiKeyItem[];
  logs: LogEntry[];
  settings?: SystemSettings;
  logFilter: "all" | "api" | "user" | "system" | "error";
  loading: boolean;
  error: string;

  setSection: (section: AdminSection) => void;
  setLogFilter: (filter: AdminStore["logFilter"]) => void;
  clearError: () => void;
  hydrate: (runner: <T>(fn: (token: string) => Promise<T>) => Promise<T>) => Promise<void>;
  toggleUserBlock: (
    runner: <T>(fn: (token: string) => Promise<T>) => Promise<T>,
    userId: string,
    blocked: boolean,
  ) => Promise<void>;
  toggleModelEnabled: (id: string) => void;
}

export const useAdminStore = create<AdminStore>((set, get) => ({
  section: "dashboard",
  users: [],
  usage: [],
  models: [],
  dashboard: undefined,
  modelConfigs: [],
  apiKeys: [],
  logs: [],
  settings: undefined,
  logFilter: "all",
  loading: false,
  error: "",

  setSection: (section) => set({ section }),
  setLogFilter: (logFilter) => set({ logFilter }),
  clearError: () => set({ error: "" }),

  hydrate: async (runner) => {
    set({ loading: true, error: "" });
    try {
      const [users, usage, models, dashboard, apiKeys, logs, settings] = await Promise.all([
        runner((token) => adminListUsers(token)),
        runner((token) => adminDailyUsage(token)),
        runner((token) => getModels(token)),
        getDashboardStats(),
        getApiKeys(),
        getLogs(),
        getSettings(),
      ]);

      const modelConfigs = await getModelsConfig(models);
      set({ users, usage, models, dashboard, modelConfigs, apiKeys, logs, settings, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "管理员数据加载失败",
        loading: false,
      });
      throw err;
    }
  },

  toggleUserBlock: async (runner, userId, blocked) => {
    try {
      await runner((token) => adminBlockUser(token, userId, blocked));
      const users = await runner((token) => adminListUsers(token));
      set({ users });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "用户状态更新失败" });
      throw err;
    }
  },

  toggleModelEnabled: (id) => {
    set((state) => ({
      modelConfigs: state.modelConfigs.map((item) =>
        item.id === id
          ? {
              ...item,
              enabled: !item.enabled,
            }
          : item,
      ),
    }));
  },
}));
