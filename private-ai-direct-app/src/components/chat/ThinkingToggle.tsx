import type { ThinkingMode } from "../../types/api";

interface ThinkingToggleProps {
  value: ThinkingMode;
  disabled?: boolean;
  onChange: (mode: ThinkingMode) => void;
}

export function ThinkingToggle({ value, disabled, onChange }: ThinkingToggleProps) {
  return (
    <div className="thinking-switch" role="group" aria-label="思考模式">
      <button
        type="button"
        className={value === "standard" ? "thinking-btn active" : "thinking-btn"}
        onClick={() => onChange("standard")}
        disabled={disabled}
      >
        标准
      </button>
      <button
        type="button"
        className={value === "thinking" ? "thinking-btn active" : "thinking-btn"}
        onClick={() => onChange("thinking")}
        disabled={disabled}
      >
        思考
      </button>
    </div>
  );
}
