import { useMemo, useState } from "react";

import type { ConversationSummary } from "../../types/api";
import { initials } from "../../utils/format";

interface ChatSidebarProps {
  username: string;
  roleLabel: string;
  conversations: ConversationSummary[];
  activeConversationId?: string;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onOpenSettings: () => void;
}

export function ChatSidebar({
  username,
  roleLabel,
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onOpenSettings,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("");

  const filteredConversations = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return conversations;
    return conversations.filter((conversation) => conversation.title.toLowerCase().includes(keyword));
  }, [conversations, search]);

  return (
    <aside className="sidebar">
      <div className="brand-header">
        <div className="logo-box">H</div>
        <span className="brand-name">AI Hub</span>
      </div>

      <button className="btn-new-chat" type="button" onClick={onNewChat} aria-label="新建会话">
        <div className="left-group">
          <span className="btn-new-icon">＋</span>
          新建会话
        </div>
        <span className="shortcut">⌘ K</span>
      </button>

      <div className="history-wrapper">
        <div className="history-label">
          <span className="history-label-icon">◷</span>
          历史会话
        </div>

        <div className="history-search-wrap">
          <input
            className="history-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索会话..."
            aria-label="搜索会话"
          />
        </div>

        {filteredConversations.length === 0 ? (
          <div className="history-empty">{search ? "没有匹配的会话" : "暂无会话，点击上方新建"}</div>
        ) : (
          filteredConversations.map((conversation) => (
            <div
              key={conversation.id}
              className={conversation.id === activeConversationId ? "history-item active" : "history-item"}
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
              <span className="history-item-title">{conversation.title}</span>
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
                删除
              </button>
            </div>
          ))
        )}

        {conversations.length > 6 ? <div className="history-more">查看全部</div> : null}
      </div>

      <div className="sidebar-bottom">
        <button
          className="bottom-action"
          type="button"
          onClick={() => window.alert("移动端应用入口开发中")}
          aria-label="查看手机应用"
        >
          <span>查看手机应用</span>
          <span>📱</span>
        </button>

        <button className="bottom-action" type="button" onClick={onOpenSettings} aria-label="账号设置">
          <div className="user-block">
            <div className="avatar-box">{initials(username).slice(0, 1)}</div>
            {username}
            <span className="role-tag">{roleLabel}</span>
          </div>
          <span>⌄</span>
        </button>
      </div>
    </aside>
  );
}
