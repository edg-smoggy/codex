import { create } from "zustand";

import type { AuthBundle, UserRole } from "../types/api";
import { login, refresh, register } from "../api/auth";
import { isUnauthorizedError } from "../api/http";

const STORAGE_KEY = "private_ai_auth";

interface AuthStore {
  bundle: AuthBundle | null;
  hydrated: boolean;
  loading: boolean;
  error: string;
  init: () => void;
  clearError: () => void;
  loginWithPassword: (username: string, password: string, expectedRole?: UserRole) => Promise<void>;
  registerWithInvite: (inviteCode: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  withAuthRetry: <T>(fn: (accessToken: string) => Promise<T>) => Promise<T>;
}

function saveBundle(bundle: AuthBundle | null) {
  if (!bundle) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(bundle));
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  bundle: null,
  hydrated: false,
  loading: false,
  error: "",

  init: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        set({ bundle: JSON.parse(raw) as AuthBundle, hydrated: true });
        return;
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    set({ hydrated: true, bundle: null });
  },

  clearError: () => set({ error: "" }),

  loginWithPassword: async (username: string, password: string, expectedRole?: UserRole) => {
    set({ loading: true, error: "" });
    try {
      const next = await login({ username, password });
      if (expectedRole && next.user.role !== expectedRole) {
        const roleText = expectedRole === "admin" ? "管理员" : "成员";
        throw new Error(`该账号不是${roleText}账号，请切换登录入口`);
      }
      saveBundle(next);
      set({ bundle: next, loading: false, error: "" });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "登录失败",
      });
      throw err;
    }
  },

  registerWithInvite: async (inviteCode: string, username: string, password: string) => {
    set({ loading: true, error: "" });
    try {
      const next = await register({ inviteCode, username, password });
      saveBundle(next);
      set({ bundle: next, loading: false, error: "" });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "注册失败",
      });
      throw err;
    }
  },

  logout: () => {
    saveBundle(null);
    set({ bundle: null, error: "" });
  },

  withAuthRetry: async <T>(fn: (accessToken: string) => Promise<T>): Promise<T> => {
    const current = get().bundle;
    if (!current) throw new Error("Not logged in");

    try {
      return await fn(current.token.access_token);
    } catch (err) {
      if (!isUnauthorizedError(err)) {
        throw err;
      }

      const next = await refresh(current.token.refresh_token);
      saveBundle(next);
      set({ bundle: next });
      return fn(next.token.access_token);
    }
  },
}));
