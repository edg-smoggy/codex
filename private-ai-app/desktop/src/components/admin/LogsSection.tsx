import type { LogEntry } from "../../types/view";

interface LogsSectionProps {
  filter: "all" | "api" | "user" | "system" | "error";
  logs: LogEntry[];
  onFilterChange: (filter: "all" | "api" | "user" | "system" | "error") => void;
}

const FILTERS: Array<{ id: "all" | "api" | "user" | "system" | "error"; label: string }> = [
  { id: "all", label: "全部" },
  { id: "api", label: "API 调用" },
  { id: "user", label: "用户操作" },
  { id: "system", label: "系统事件" },
  { id: "error", label: "错误" },
];

export function LogsSection({ filter, logs, onFilterChange }: LogsSectionProps) {
  const filtered = filter === "all" ? logs : logs.filter((item) => item.type === filter);

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
            <div className="log-dot" style={{ background: log.color }} />
            <div className="log-content">
              <div className="log-text">{log.text}</div>
              <div className="log-meta">{log.meta}</div>
            </div>
            <div className="log-time">{log.time}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
