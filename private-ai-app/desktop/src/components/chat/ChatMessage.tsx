import { isValidElement, useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import type { MessageItem } from "../../types/api";
import { useAuthStore } from "../../stores/authStore";
import { formatTimeShort } from "../../utils/format";

interface ChatMessageProps {
  message: MessageItem;
  modelName?: string;
  canRegenerate?: boolean;
  onRegenerate?: () => void;
}

function getNodeText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map((item) => getNodeText(item)).join("");
  }
  if (isValidElement(node)) {
    return getNodeText(node.props.children as ReactNode);
  }
  return "";
}

async function copyToClipboard(text: string): Promise<void> {
  if (!text) return;
  await navigator.clipboard.writeText(text);
}

function MarkdownPre({ children, ...props }: ComponentPropsWithoutRef<"pre">) {
  const [copied, setCopied] = useState(false);
  const codeText = useMemo(() => getNodeText(children).replace(/\n$/, ""), [children]);

  return (
    <div className="md-pre-wrap">
      <button
        className="code-copy-btn"
        type="button"
        onClick={() => {
          void copyToClipboard(codeText)
            .then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1200);
            })
            .catch(() => undefined);
        }}
        aria-label="复制代码"
      >
        {copied ? "已复制" : "复制代码"}
      </button>
      <pre {...props}>{children}</pre>
    </div>
  );
}

export function ChatMessage({ message, modelName, canRegenerate, onRegenerate }: ChatMessageProps) {
  const [copiedMessage, setCopiedMessage] = useState(false);
  const username = useAuthStore((state) => state.bundle?.user.username || "U");

  const isUser = message.role === "user";
  const sender = isUser ? "你" : modelName || "AI";
  const userInitial = username.charAt(0).toUpperCase() || "U";

  return (
    <div className="message">
      <div className={isUser ? "message-avatar user-avatar-msg" : "message-avatar ai-avatar-msg"}>{isUser ? userInitial : "✦"}</div>
      <div className="message-content">
        <div className="message-header">
          <span className="message-sender">{sender}</span>
          <span className="message-time">{formatTimeShort(message.created_at)}</span>
        </div>
        <div className="message-actions">
          <button
            className="message-action-btn"
            type="button"
            onClick={() => {
              void copyToClipboard(message.content)
                .then(() => {
                  setCopiedMessage(true);
                  window.setTimeout(() => setCopiedMessage(false), 1000);
                })
                .catch(() => undefined);
            }}
          >
            {copiedMessage ? "已复制" : "复制"}
          </button>
          {!isUser && canRegenerate && onRegenerate ? (
            <button className="message-action-btn" type="button" onClick={onRegenerate}>
              重新生成
            </button>
          ) : null}
        </div>
        <div className="message-body markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={{ pre: MarkdownPre }}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
