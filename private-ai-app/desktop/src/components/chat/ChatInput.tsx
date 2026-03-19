import { useEffect, useRef } from "react";

interface ChatInputProps {
  value: string;
  disabled?: boolean;
  streaming?: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}

export function ChatInput({ value, disabled, streaming, onChange, onSend, onStop }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "auto";
    ref.current.style.height = `${Math.min(ref.current.scrollHeight, 150)}px`;
  }, [value]);

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <div className="input-box">
          <textarea
            ref={ref}
            id="msgInput"
            rows={1}
            placeholder="发送消息..."
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.nativeEvent.isComposing) return;
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                onSend();
              }
            }}
            aria-label="消息输入框"
          />
          <div className="input-actions">
            <button
              className="input-action-btn"
              type="button"
              title="文件上传功能开发中"
              aria-label="上传文件"
              disabled
            >
              📎
            </button>
            {streaming ? (
              <button className="stop-btn" type="button" onClick={onStop} aria-label="停止生成">
                ⏹
              </button>
            ) : (
              <button className="send-btn" type="button" disabled={disabled} onClick={onSend} aria-label="发送消息">
                ↗
              </button>
            )}
          </div>
        </div>
        <div className="input-hint">Enter 换行，Ctrl/⌘ + Enter 发送。AI Hub 可能会犯错，请核实重要信息</div>
      </div>
    </div>
  );
}
