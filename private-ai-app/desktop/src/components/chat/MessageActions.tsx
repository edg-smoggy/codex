import { useState } from "react";

interface MessageActionsProps {
  canRegenerate?: boolean;
  onCopy: () => Promise<void>;
  onRegenerate?: () => void;
}

export function MessageActions({ canRegenerate, onCopy, onRegenerate }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  return (
    <div className="message-actions">
      <button
        className="msg-act-icon"
        type="button"
        title={copied ? "已复制" : "复制"}
        aria-label="复制消息"
        onClick={() => {
          void onCopy()
            .then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1200);
            })
            .catch(() => undefined);
        }}
      >
        {copied ? "✓" : "📋"}
      </button>

      {canRegenerate && onRegenerate ? (
        <button className="msg-act-icon" type="button" title="重新生成" aria-label="重新生成" onClick={onRegenerate}>
          🔄
        </button>
      ) : null}

      <button
        className="msg-act-icon"
        type="button"
        title="有帮助"
        aria-label="有帮助"
        onClick={() => window.alert("感谢反馈，我们已记录。")}
      >
        👍
      </button>

      <button
        className="msg-act-icon"
        type="button"
        title="没有帮助"
        aria-label="没有帮助"
        onClick={() => window.alert("已收到反馈，我们会持续优化。")}
      >
        👎
      </button>
    </div>
  );
}
