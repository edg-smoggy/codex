import type { AdminUsageItem, AdminUserItem } from "../../types/api";
import type { DashboardStats } from "../../types/view";
import { toCurrency } from "../../utils/format";

interface DashboardSectionProps {
  stats?: DashboardStats;
  users: AdminUserItem[];
  usage: AdminUsageItem[];
  onGotoUsers: () => void;
}

export function DashboardSection({ stats, users, usage, onGotoUsers }: DashboardSectionProps) {
  if (!stats) return null;

  const topUsers = usage
    .slice()
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 5);

  const totalDistribution = stats.modelDistribution.reduce((sum, item) => sum + item.value, 0) || 1;

  return (
    <section className="page-section active">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
              👥
            </div>
            <div className="stat-change stat-up">{stats.userDelta}</div>
          </div>
          <div className="stat-value">{stats.totalUsers}</div>
          <div className="stat-label">总用户数</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--green-bg)", color: "var(--green)" }}>
              💬
            </div>
            <div className="stat-change stat-up">{stats.convDelta}</div>
          </div>
          <div className="stat-value">{stats.todayConversations.toLocaleString()}</div>
          <div className="stat-label">今日对话数</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--orange-bg)", color: "var(--orange)" }}>
              ⚡
            </div>
            <div className="stat-change stat-down">{stats.costDelta}</div>
          </div>
          <div className="stat-value">{toCurrency(stats.todayCost)}</div>
          <div className="stat-label">今日 API 花费</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--blue-bg)", color: "var(--blue)" }}>
              🤖
            </div>
            <div className="stat-change stat-up">{stats.modelDelta}</div>
          </div>
          <div className="stat-value">{stats.availableModels}</div>
          <div className="stat-label">可用模型数</div>
        </div>
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <div className="chart-title">
            <span>API 调用趋势</span>
            <div className="chart-period">
              <button type="button" className="period-btn active">
                7天
              </button>
              <button type="button" className="period-btn">
                30天
              </button>
              <button type="button" className="period-btn">
                90天
              </button>
            </div>
          </div>
          <div className="chart-bars">
            {stats.trend.map((item) => (
              <div className="chart-bar-group" key={item.label}>
                <div className="chart-bar" style={{ height: `${(item.value / 100) * 160}px` }} />
                <div className="chart-bar-label">{item.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-title">
            <span>模型用量分布</span>
          </div>
          <div className="donut-container">
            <div className="donut-ring">
              <div className="donut-hole">
                <div className="donut-total">{stats.todayConversations.toLocaleString()}</div>
                <div className="donut-sublabel">总调用</div>
              </div>
            </div>
            <div className="donut-legend">
              {stats.modelDistribution.map((item) => (
                <div className="legend-item" key={item.label}>
                  <span className="legend-dot" style={{ background: item.color }} />
                  {item.label} · {Math.round((item.value / totalDistribution) * 100)}%
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="table-card">
        <div className="table-header">
          <span className="table-title">近期活跃用户</span>
          <button type="button" className="btn btn-ghost" onClick={onGotoUsers}>
            查看全部 →
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>今日 Token</th>
              <th>今日花费</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {topUsers.map((item) => {
              const user = users.find((entry) => entry.id === item.user_id);
              return (
                <tr key={item.user_id}>
                  <td>
                    <div className="user-cell">
                      <div className="user-cell-avatar" style={{ background: "linear-gradient(135deg,#6c5ce7,#a29bfe)" }}>
                        {item.username.slice(0, 1)}
                      </div>
                      <div className="user-cell-info">
                        <div className="user-cell-name">{item.username}</div>
                        <div className="user-cell-email">{user?.role === "admin" ? "管理员" : "成员"}</div>
                      </div>
                    </div>
                  </td>
                  <td>{item.total_tokens.toLocaleString()}</td>
                  <td>{toCurrency(item.total_cost)}</td>
                  <td>
                    <span className={user?.status === "blocked" ? "status-badge status-banned" : "status-badge status-active"}>
                      ● {user?.status === "blocked" ? "已禁用" : "正常"}
                    </span>
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
