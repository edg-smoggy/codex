import { useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";

import { AdminSidebar } from "../components/admin/AdminSidebar";
import { DashboardSection } from "../components/admin/DashboardSection";
import { KeysSection } from "../components/admin/KeysSection";
import { LogsSection } from "../components/admin/LogsSection";
import { ModelsSection } from "../components/admin/ModelsSection";
import { SettingsSection } from "../components/admin/SettingsSection";
import { UsersSection } from "../components/admin/UsersSection";
import { useAdminStore } from "../stores/adminStore";
import { useAuthStore } from "../stores/authStore";
import { useUiStore } from "../stores/uiStore";

const SECTION_TITLE = {
  dashboard: "仪表盘",
  users: "用户管理",
  models: "模型管理",
  keys: "API 密钥",
  logs: "使用日志",
  settings: "系统设置",
} as const;

export function AdminPage() {
  const navigate = useNavigate();

  const { bundle, withAuthRetry, logout } = useAuthStore(
    useShallow((state) => ({
      bundle: state.bundle,
      withAuthRetry: state.withAuthRetry,
      logout: state.logout,
    })),
  );

  const admin = useAdminStore(
    useShallow((state) => ({
      section: state.section,
      users: state.users,
      usage: state.usage,
      dashboard: state.dashboard,
      modelConfigs: state.modelConfigs,
      apiKeys: state.apiKeys,
      logs: state.logs,
      settings: state.settings,
      logFilter: state.logFilter,
      loading: state.loading,
      error: state.error,
      setSection: state.setSection,
      setLogFilter: state.setLogFilter,
      hydrate: state.hydrate,
      toggleUserBlock: state.toggleUserBlock,
      toggleModelEnabled: state.toggleModelEnabled,
    })),
  );

  const ui = useUiStore(
    useShallow((state) => ({
      adminSidebarOpen: state.adminSidebarOpen,
      toggleAdminSidebar: state.toggleAdminSidebar,
      closeAdminSidebar: state.closeAdminSidebar,
    })),
  );

  useEffect(() => {
    admin.hydrate(withAuthRetry).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle?.token.access_token]);

  const pageTitle = useMemo(() => SECTION_TITLE[admin.section], [admin.section]);

  return (
    <div className="admin-layout">
      <AdminSidebar
        active={admin.section}
        username={bundle?.user.username || "admin"}
        open={ui.adminSidebarOpen}
        onChange={admin.setSection}
        onCloseMobile={ui.closeAdminSidebar}
      />

      <main className="admin-main">
        <div className="admin-topbar">
          <div className="topbar-left">
            <button className="topbar-btn mobile-only" type="button" onClick={ui.toggleAdminSidebar} aria-label="切换管理侧栏">
              ☰
            </button>
            <div className="topbar-title">{pageTitle}</div>
          </div>
          <div className="topbar-actions">
            <div className="search-box">
              <span className="search-icon">🔍</span>
              <input placeholder="搜索用户、模型、日志..." aria-label="全局搜索" />
            </div>
            <Link to="/chat" className="topbar-pill">
              返回聊天
            </Link>
            <button
              className="topbar-btn"
              type="button"
              aria-label="退出登录"
              onClick={() => {
                logout();
                navigate("/auth", { replace: true });
              }}
            >
              ⎋
            </button>
          </div>
        </div>

        <div className="content-area">
          {admin.error ? <div className="error-box">{admin.error}</div> : null}
          {admin.loading ? <div className="loading-block">加载中...</div> : null}

          {!admin.loading && admin.section === "dashboard" ? (
            <DashboardSection
              stats={admin.dashboard}
              users={admin.users}
              usage={admin.usage}
              onGotoUsers={() => admin.setSection("users")}
            />
          ) : null}

          {!admin.loading && admin.section === "users" ? (
            <UsersSection
              users={admin.users}
              usage={admin.usage}
              onToggleUserBlock={(userId, blocked) => {
                void admin.toggleUserBlock(withAuthRetry, userId, blocked);
              }}
            />
          ) : null}

          {!admin.loading && admin.section === "models" ? (
            <ModelsSection models={admin.modelConfigs} onToggle={admin.toggleModelEnabled} />
          ) : null}

          {!admin.loading && admin.section === "keys" ? <KeysSection keys={admin.apiKeys} /> : null}

          {!admin.loading && admin.section === "logs" ? (
            <LogsSection filter={admin.logFilter} logs={admin.logs} onFilterChange={admin.setLogFilter} />
          ) : null}

          {!admin.loading && admin.section === "settings" ? <SettingsSection settings={admin.settings} /> : null}
        </div>
      </main>

      <div className={ui.adminSidebarOpen ? "sidebar-overlay show" : "sidebar-overlay"} onClick={ui.closeAdminSidebar} role="presentation" />
    </div>
  );
}
