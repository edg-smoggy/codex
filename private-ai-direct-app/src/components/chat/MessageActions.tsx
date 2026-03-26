import { useState } from "react";

interface MessageActionsProps {
  canRegenerate?: boolean;
  onCopy: () => Promise<void>;
  onRegenerate?: () => void;
}

export function MessageActions({ canRegenerate, onCopy, onRegenerate }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  return (
    <div className="tool-bar">
      <button
        className="tool-btn"
        type="button"
        title={copied ? "已复制" : "复制全文"}
        aria-label="复制全文"
        onClick={() => {
          void onCopy()
            .then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1200);
            })
            .catch(() => undefined);
        }}
      >
        {copied ? "✓" : "⎘"}
      </button>

      {canRegenerate && onRegenerate ? (
        <button className="tool-btn" type="button" title="重新生成" aria-label="重新生成" onClick={onRegenerate}>
          ↻
        </button>
      ) : null}

      <button
        className="tool-btn"
        type="button"
        title="赞同"
        aria-label="赞同"
        onClick={() => window.alert("感谢反馈，我们已记录。")}
      >
        👍
      </button>

      <button
        className="tool-btn"
        type="button"
        title="反对"
        aria-label="反对"
        onClick={() => window.alert("已收到反馈，我们会持续优化。")}
      >
        👎
      </button>
    </div>
  );
}
