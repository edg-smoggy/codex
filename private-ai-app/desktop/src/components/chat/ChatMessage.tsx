import { isValidElement, useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import type { MessageItem } from "../../types/api";
import { MessageActions } from "./MessageActions";

interface ChatMessageProps {
  message: MessageItem;
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

function MarkdownTable({ children, ...props }: ComponentPropsWithoutRef<"table">) {
  return (
    <div className="table-container">
      <table className="modern-table" {...props}>
        {children}
      </table>
    </div>
  );
}

export function ChatMessage({ message, canRegenerate, onRegenerate }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "msg-block is-user" : "msg-block is-ai"}>
      {isUser ? (
        <div className="bubble-user">{message.content}</div>
      ) : (
        <>
          <div className="bubble-ai rich-text">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={{ pre: MarkdownPre, table: MarkdownTable }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          <MessageActions onCopy={() => copyToClipboard(message.content)} canRegenerate={canRegenerate} onRegenerate={onRegenerate} />
        </>
      )}
    </div>
  );
}
