export function formatRelativeDateTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

export function formatTimeShort(ts: string): string {
  return new Date(ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

export function toCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}

export function initials(name: string): string {
  if (!name) return "U";
  return name.slice(0, 1).toUpperCase();
}
