import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import type { MessageItem } from "../../types/api";
import { formatTimeShort } from "../../utils/format";

interface ChatMessageProps {
  message: MessageItem;
  modelName?: string;
}

export function ChatMessage({ message, modelName }: ChatMessageProps) {
  const isUser = message.role === "user";
  const sender = isUser ? "你" : modelName || "AI";

  return (
    <div className="message">
      <div className={isUser ? "message-avatar user-avatar-msg" : "message-avatar ai-avatar-msg"}>{isUser ? "K" : "✦"}</div>
      <div className="message-content">
        <div className="message-header">
          <span className="message-sender">{sender}</span>
          <span className="message-time">{formatTimeShort(message.created_at)}</span>
        </div>
        <div className="message-body markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
