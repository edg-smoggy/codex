import { useEffect, useRef } from "react";

import type { ThinkingMode } from "../../types/api";
import { ThinkingToggle } from "./ThinkingToggle";

interface ChatInputProps {
  value: string;
  modelName: string;
  modelColor?: string;
  showThinkingMode?: boolean;
  thinkingMode?: ThinkingMode;
  disabled?: boolean;
  streaming?: boolean;
  onChange: (value: string) => void;
  onThinkingModeChange?: (mode: ThinkingMode) => void;
  onOpenModelModal: () => void;
  onSend: () => void;
  onStop: () => void;
}

export function ChatInput({
  value,
  modelName,
  modelColor,
  showThinkingMode,
  thinkingMode = "standard",
  disabled,
  streaming,
  onChange,
  onThinkingModeChange,
  onOpenModelModal,
  onSend,
  onStop,
}: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "auto";
    ref.current.style.height = `${Math.min(ref.current.scrollHeight, 160)}px`;
  }, [value]);

  return (
    <div className="input-dock">
      <div className="input-area-wrapper">
        <div className="input-left-actions">
          {showThinkingMode && onThinkingModeChange ? (
            <ThinkingToggle value={thinkingMode} onChange={onThinkingModeChange} disabled={streaming} />
          ) : null}
          <button className="btn-attach" type="button" title="文件上传功能开发中" aria-label="上传附件" disabled>
            +
          </button>
        </div>

        <textarea
          ref={ref}
          id="msgInput"
          className="core-input"
          rows={1}
          placeholder="尽管问，带图也行"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) return;
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              onSend();
            }
          }}
          aria-label="消息输入框"
        />

        <div className="input-right-actions">
          <button className="model-badge" type="button" onClick={onOpenModelModal} aria-label="选择模型">
            <span className="model-dot" style={{ background: modelColor || "var(--brand-primary)" }} />
            <span>{modelName}</span>
            <span>⌄</span>
          </button>

          {streaming ? (
            <button className="btn-submit" type="button" onClick={onStop} aria-label="停止生成" title="停止生成">
              ■
            </button>
          ) : (
            <button className="btn-submit" type="button" disabled={disabled} onClick={onSend} aria-label="发送消息" title="发送">
              ↑
            </button>
          )}
        </div>
      </div>

      <div className="footer-note">Enter 换行，Ctrl/⌘ + Enter 发送。内容由 AI 生成，请仔细甄别</div>
    </div>
  );
}
