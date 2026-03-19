import type { AdminUsageItem, AdminUserItem } from "../../types/api";
import type { DashboardStats } from "../../types/view";
import { toCurrency } from "../../utils/format";

interface DashboardSectionProps {
  stats?: DashboardStats;
  users: AdminUserItem[];
  usage: AdminUsageItem[];
  onGotoUsers: () => void;
}

const DONUT_COLORS = [
  "var(--accent)",
  "var(--green)",
  "var(--orange)",
  "var(--pink)",
  "var(--blue)",
  "#7f8fa6",
  "#a29bfe",
];

function buildDonutGradient(stats: DashboardStats): { gradient: string; legend: Array<{ label: string; value: number; color: string }> } {
  const total = stats.daily_usage_7d.reduce((sum, item) => sum + item.tokens, 0);
  if (!total) {
    return {
      gradient: "conic-gradient(var(--bg-active) 0deg 360deg)",
      legend: [],
    };
  }

  const legend: Array<{ label: string; value: number; color: string }> = [];
  let start = 0;
  const pieces: string[] = [];

  stats.daily_usage_7d.forEach((item, index) => {
    const ratio = item.tokens / total;
    const angle = ratio * 360;
    const color = DONUT_COLORS[index % DONUT_COLORS.length];
    const end = start + angle;
    pieces.push(`${color} ${start}deg ${end}deg`);
    legend.push({ label: item.date, value: item.tokens, color });
    start = end;
  });

  return {
    gradient: `conic-gradient(${pieces.join(", ")})`,
    legend,
  };
}

export function DashboardSection({ stats, users, usage, onGotoUsers }: DashboardSectionProps) {
  if (!stats) return null;

  const topUsers = usage
    .slice()
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 5);

  const maxTokens = Math.max(...stats.daily_usage_7d.map((item) => item.tokens), 1);
  const donut = buildDonutGradient(stats);
  const totalDistribution = donut.legend.reduce((sum, item) => sum + item.value, 0) || 1;

  return (
    <section className="page-section active">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
              👥
            </div>
          </div>
          <div className="stat-value">{stats.total_users.toLocaleString()}</div>
          <div className="stat-label">总用户数</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--green-bg)", color: "var(--green)" }}>
              🟢
            </div>
          </div>
          <div className="stat-value">{stats.active_users_today.toLocaleString()}</div>
          <div className="stat-label">今日活跃用户</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--blue-bg)", color: "var(--blue)" }}>
              💬
            </div>
          </div>
          <div className="stat-value">{stats.total_conversations.toLocaleString()}</div>
          <div className="stat-label">总对话数</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon" style={{ background: "var(--orange-bg)", color: "var(--orange)" }}>
              ⚡
            </div>
          </div>
          <div className="stat-value">{toCurrency(stats.total_cost_today)}</div>
          <div className="stat-label">今日 API 花费</div>
        </div>
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <div className="chart-title">
            <span>最近 7 天 Token 趋势</span>
          </div>
          <div className="chart-bars">
            {stats.daily_usage_7d.map((item) => {
              const barHeight = Math.max(8, Math.round((item.tokens / maxTokens) * 160));
              const label = item.date.slice(5);
              return (
                <div className="chart-bar-group" key={item.date}>
                  <div className="chart-bar" style={{ height: `${barHeight}px` }} />
                  <div className="chart-bar-label">{label}</div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-title">
            <span>近 7 天 Token 占比</span>
          </div>
          <div className="donut-container">
            <div className="donut-ring" style={{ background: donut.gradient }}>
              <div className="donut-hole">
                <div className="donut-total">{stats.total_tokens_today.toLocaleString()}</div>
                <div className="donut-sublabel">今日 Tokens</div>
              </div>
            </div>
            <div className="donut-legend">
              {donut.legend.map((item) => (
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
