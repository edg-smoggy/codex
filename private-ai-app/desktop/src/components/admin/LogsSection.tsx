import type { LogEntry } from "../../types/view";

type LogFilter = "all" | "chat" | "auth" | "admin" | "error";

interface LogsSectionProps {
  filter: LogFilter;
  logs: LogEntry[];
  onFilterChange: (filter: LogFilter) => void;
}

const FILTERS: Array<{ id: LogFilter; label: string }> = [
  { id: "all", label: "全部" },
  { id: "chat", label: "聊天" },
  { id: "auth", label: "认证" },
  { id: "admin", label: "管理" },
  { id: "error", label: "错误" },
];

function isMatch(filter: LogFilter, action: string): boolean {
  if (filter === "all") return true;
  if (filter === "error") return action.includes("error");
  return action.startsWith(`${filter}.`);
}

function dotColor(action: string): string {
  if (action.includes("error")) return "var(--red)";
  if (action.startsWith("chat.")) return "var(--accent)";
  if (action.startsWith("auth.")) return "var(--blue)";
  if (action.startsWith("admin.")) return "var(--orange)";
  return "var(--green)";
}

export function LogsSection({ filter, logs, onFilterChange }: LogsSectionProps) {
  const filtered = logs.filter((item) => isMatch(filter, item.action));

  return (
    <section className="page-section active">
      <div className="log-filters">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === filter ? "filter-chip active" : "filter-chip"}
            onClick={() => onFilterChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="table-card">
        {filtered.map((log) => (
          <div className="log-entry" key={log.id}>
            <div className="log-dot" style={{ background: dotColor(log.action) }} />
            <div className="log-content">
              <div className="log-text">
                <strong>{log.action}</strong>
                {log.username ? ` · ${log.username}` : ""}
              </div>
              <div className="log-meta">
                {Object.keys(log.detail).length ? JSON.stringify(log.detail) : "无附加信息"}
              </div>
            </div>
            <div className="log-time">{new Date(log.created_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
