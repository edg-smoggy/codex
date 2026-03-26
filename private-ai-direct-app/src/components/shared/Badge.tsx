import type { ReactNode } from "react";

interface BadgeProps {
  className?: string;
  children: ReactNode;
}

export function Badge({ className = "", children }: BadgeProps) {
  return <span className={`status-badge ${className}`.trim()}>{children}</span>;
}
