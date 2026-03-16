import type { AdminUsageItem, AdminUserItem } from "../../types/api";

interface UsersSectionProps {
  users: AdminUserItem[];
  usage: AdminUsageItem[];
  onToggleUserBlock: (userId: string, blocked: boolean) => void;
}

export function UsersSection({ users, usage, onToggleUserBlock }: UsersSectionProps) {
  const usageMap = new Map(usage.map((item) => [item.user_id, item]));

  return (
    <section className="page-section active">
      <div className="table-card">
        <div className="table-header">
          <span className="table-title">全部用户 ({users.length})</span>
          <div className="table-actions">
            <button type="button" className="btn btn-ghost">
              📥 导出
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>角色</th>
              <th>日额度(Token)</th>
              <th>已用</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const used = usageMap.get(user.id);
              return (
                <tr key={user.id}>
                  <td>
                    <div className="user-cell">
                      <div className="user-cell-avatar" style={{ background: "linear-gradient(135deg,#6c5ce7,#a29bfe)" }}>
                        {user.username.slice(0, 1).toUpperCase()}
                      </div>
                      <div className="user-cell-info">
                        <div className="user-cell-name">{user.username}</div>
                        <div className="user-cell-email">{user.id.slice(0, 8)}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="status-badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                      {user.role === "admin" ? "管理员" : "成员"}
                    </span>
                  </td>
                  <td>{user.daily_token_limit.toLocaleString()}</td>
                  <td>{(used?.total_tokens || 0).toLocaleString()}</td>
                  <td>
                    <span className={user.status === "blocked" ? "status-badge status-banned" : "status-badge status-active"}>
                      ● {user.status === "blocked" ? "已禁用" : "正常"}
                    </span>
                  </td>
                  <td style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
                    {new Date(user.created_at).toLocaleDateString("zh-CN")}
                  </td>
                  <td>
                    {user.role === "admin" ? (
                      <span className="status-badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                        管理员
                      </span>
                    ) : (
                      <button
                        type="button"
                        className={user.status === "blocked" ? "btn btn-ghost" : "btn btn-danger"}
                        onClick={() => onToggleUserBlock(user.id, user.status !== "blocked")}
                      >
                        {user.status === "blocked" ? "解封" : "封禁"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
