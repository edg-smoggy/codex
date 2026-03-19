import type { ConversationSummary } from "../../types/api";
import type { UIModel } from "../../types/view";
import { getModelMeta } from "../../mocks/modelCatalog";
import { formatRelativeDateTime, initials } from "../../utils/format";

interface ChatSidebarProps {
  username: string;
  conversations: ConversationSummary[];
  activeConversationId?: string;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

function resolveModel(modelId: string): UIModel {
  const base = getModelMeta(modelId, modelId.includes("gemini") ? "gemini" : modelId.includes("moonshot") || modelId.includes("kimi") ? "kimi" : "openai");
  return {
    model: modelId,
    provider: "unknown",
    enabled: true,
    ...base,
  };
}

export function ChatSidebar({
  username,
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}: ChatSidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">H</div>
          <span className="logo-text">AI Hub</span>
        </div>
        <button className="new-chat-btn" type="button" onClick={onNewChat} aria-label="新建对话">
          <span>＋</span>
          <span>新建对话</span>
        </button>
      </div>

      <div className="sidebar-section-title">最近对话</div>
      <div className="chat-list">
        {conversations.length === 0 ? (
          <div className="sidebar-empty">暂无对话，点击上方按钮开始</div>
        ) : (
          conversations.map((conversation) => {
            const model = resolveModel(conversation.model);
            return (
              <div
                key={conversation.id}
                className={conversation.id === activeConversationId ? "chat-item active" : "chat-item"}
                role="button"
                tabIndex={0}
                onClick={() => onSelectConversation(conversation.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectConversation(conversation.id);
                  }
                }}
              >
                <div className={`chat-item-icon ${model.bgClass}`}>{model.icon}</div>
                <div className="chat-item-info">
                  <div className="chat-item-title">{conversation.title}</div>
                  <div className="chat-item-meta">
                    {model.name} · {formatRelativeDateTime(conversation.updated_at)}
                  </div>
                </div>
                <button
                  className="chat-item-delete"
                  type="button"
                  aria-label="删除会话"
                  title="删除会话"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDeleteConversation(conversation.id);
                  }}
                >
                  🗑
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <div className="user-avatar">{initials(username)}</div>
        <div className="user-info">
          <div className="user-name">{username}</div>
          <div className="user-plan">● Private Plan</div>
        </div>
      </div>
    </aside>
  );
}
