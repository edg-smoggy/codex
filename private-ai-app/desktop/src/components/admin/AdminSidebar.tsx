import type { AdminSection } from "../../stores/adminStore";

const NAV_ITEMS: Array<{ id: AdminSection; icon: string; label: string; badge?: string }> = [
  { id: "dashboard", icon: "📊", label: "仪表盘" },
  { id: "users", icon: "👥", label: "用户管理", badge: "128" },
  { id: "models", icon: "🤖", label: "模型管理" },
  { id: "keys", icon: "🔑", label: "API 密钥" },
  { id: "logs", icon: "📜", label: "使用日志" },
  { id: "settings", icon: "⚙️", label: "系统设置" },
];

interface AdminSidebarProps {
  active: AdminSection;
  username: string;
  open: boolean;
  onChange: (section: AdminSection) => void;
  onCloseMobile: () => void;
}

export function AdminSidebar({ active, username, open, onChange, onCloseMobile }: AdminSidebarProps) {
  return (
    <aside className={open ? "admin-sidebar open" : "admin-sidebar"}>
      <div className="sidebar-brand">
        <div className="brand-icon">H</div>
        <span className="brand-text">AI Hub</span>
        <span className="brand-badge">ADMIN</span>
      </div>

      <div className="nav-section">管理菜单</div>
      <div className="nav-list">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === active ? "nav-item active" : "nav-item"}
            onClick={() => {
              onChange(item.id);
              onCloseMobile();
            }}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
          </button>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="admin-avatar">{username.slice(0, 1).toUpperCase()}</div>
        <div>
          <div className="admin-name">{username}</div>
          <div className="admin-role">系统管理员</div>
        </div>
      </div>
    </aside>
  );
}
