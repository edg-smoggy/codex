import { useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { ChatInput } from "../components/chat/ChatInput";
import { ChatMessage } from "../components/chat/ChatMessage";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ModelSelectorModal } from "../components/chat/ModelSelectorModal";
import { WelcomeScreen } from "../components/chat/WelcomeScreen";
import { useAuthStore } from "../stores/authStore";
import { useChatStore } from "../stores/chatStore";
import { useUiStore } from "../stores/uiStore";

export function ChatPage() {
  const navigate = useNavigate();
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const stickToBottomRef = useRef(true);

  const { bundle, withAuthRetry, logout } = useAuthStore(
    useShallow((state) => ({
      bundle: state.bundle,
      withAuthRetry: state.withAuthRetry,
      logout: state.logout,
    })),
  );

  const chat = useChatStore(
    useShallow((state) => ({
      models: state.models,
      selectedModelId: state.selectedModelId,
      thinkingMode: state.thinkingMode,
      conversations: state.conversations,
      activeConversationId: state.activeConversationId,
      messages: state.messages,
      health: state.health,
      input: state.input,
      draftAssistant: state.draftAssistant,
      streaming: state.streaming,
      error: state.error,
      setInput: state.setInput,
      setSelectedModel: state.setSelectedModel,
      setThinkingMode: state.setThinkingMode,
      setActiveConversation: state.setActiveConversation,
      clearError: state.clearError,
      hydrateBase: state.hydrateBase,
      hydrateMessages: state.hydrateMessages,
      startNewConversation: state.startNewConversation,
      sendMessage: state.sendMessage,
      regenerateLastAssistant: state.regenerateLastAssistant,
      deleteConversation: state.deleteConversation,
      stopStreaming: state.stopStreaming,
    })),
  );

  const ui = useUiStore(
    useShallow((state) => ({
      chatSidebarOpen: state.chatSidebarOpen,
      modelModalOpen: state.modelModalOpen,
      modelSearch: state.modelSearch,
      toggleChatSidebar: state.toggleChatSidebar,
      closeChatSidebar: state.closeChatSidebar,
      openModelModal: state.openModelModal,
      closeModelModal: state.closeModelModal,
      setModelSearch: state.setModelSearch,
    })),
  );

  useEffect(() => {
    if (!bundle) return;
    chat.hydrateBase(withAuthRetry).catch((err) => {
      useChatStore.setState({ error: err instanceof Error ? err.message : "加载失败" });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle?.token.access_token]);

  useEffect(() => {
    if (!bundle) return;
    chat.hydrateMessages(withAuthRetry).catch((err) => {
      useChatStore.setState({ error: err instanceof Error ? err.message : "加载消息失败" });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat.activeConversationId, bundle?.token.access_token]);

  useEffect(() => {
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        ui.closeModelModal();
      }
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [ui]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const onScroll = () => {
      const distance = container.scrollHeight - container.scrollTop - container.clientHeight;
      stickToBottomRef.current = distance <= 120;
    };

    onScroll();
    container.addEventListener("scroll", onScroll);
    return () => container.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    stickToBottomRef.current = true;
  }, [chat.activeConversationId]);

  useEffect(() => {
    if (!stickToBottomRef.current) return;
    const lastMessage = chat.messages[chat.messages.length - 1];
    if (!lastMessage || lastMessage.role !== "assistant") return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages]);

  const selectedModel = useMemo(
    () => chat.models.find((item) => item.model === chat.selectedModelId),
    [chat.models, chat.selectedModelId],
  );

  const activeConversation = useMemo(
    () => chat.conversations.find((item) => item.id === chat.activeConversationId),
    [chat.conversations, chat.activeConversationId],
  );

  const latestAssistantId = useMemo(
    () => [...chat.messages].reverse().find((item) => item.role === "assistant")?.id,
    [chat.messages],
  );

  const hasMessages = chat.messages.length > 0;
  const canSend = chat.input.trim().length > 0 && Boolean(chat.selectedModelId) && !chat.streaming;
  const isKimiModel = selectedModel?.provider === "kimi";

  return (
    <div className={ui.chatSidebarOpen ? "app-layout chat-refined sidebar-open" : "app-layout chat-refined"}>
      <ChatSidebar
        username={bundle?.user.username || "User"}
        roleLabel={bundle?.user.role === "admin" ? "Admin" : "Member"}
        conversations={chat.conversations}
        activeConversationId={chat.activeConversationId}
        onNewChat={() => {
          chat.startNewConversation();
          ui.closeChatSidebar();
        }}
        onSelectConversation={(id) => {
          chat.setActiveConversation(id);
          ui.closeChatSidebar();
        }}
        onDeleteConversation={(id) => {
          void chat.deleteConversation(withAuthRetry, id);
        }}
        onOpenSettings={() => {
          if (bundle?.user.role === "admin") {
            navigate("/admin");
            return;
          }
          window.alert("设置页开发中，管理员可进入后台查看设置。");
        }}
      />

      <main className="main-view">
        <header className="top-bar">
          <div className="top-left-group">
            <button className="icon-btn-ghost mobile-menu-btn" type="button" onClick={ui.toggleChatSidebar} aria-label="切换侧栏">
              ☰
            </button>

            <button className="model-dropdown" type="button" aria-label="当前会话">
              <span>{activeConversation?.title || "新会话"}</span>
              <span className="chevron">⌄</span>
            </button>
          </div>

          <div className="top-right-group">
            <div className="status-pill">
              <span className={chat.health?.api === "ok" ? "status-dot status-ok" : "status-dot status-warn"} />
              {chat.health?.api === "ok" ? "在线" : "检查中"}
            </div>

            {bundle?.user.role === "admin" ? (
              <button className="topbar-pill" type="button" onClick={() => navigate("/admin")} aria-label="进入管理后台">
                管理后台
              </button>
            ) : null}

            <button className="icon-btn-ghost" type="button" onClick={() => void chat.hydrateBase(withAuthRetry)} aria-label="刷新">
              ↻
            </button>

            <button
              className="icon-btn-ghost"
              type="button"
              onClick={() => {
                logout();
                navigate("/auth", { replace: true });
              }}
              aria-label="退出登录"
            >
              ⎋
            </button>
          </div>
        </header>

        <div className="chat-stream" id="chatMessages" ref={messagesContainerRef}>
          <div className="chat-max-width">
            {!hasMessages && !chat.draftAssistant ? (
              <WelcomeScreen
                models={chat.models}
                selectedModelId={chat.selectedModelId}
                onChooseModel={(id) => chat.setSelectedModel(id)}
                onUsePrompt={(text) => {
                  chat.setInput(text);
                  void chat.sendMessage(withAuthRetry);
                }}
              />
            ) : (
              <>
                {chat.messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    canRegenerate={message.id === latestAssistantId}
                    onRegenerate={() => void chat.regenerateLastAssistant(withAuthRetry)}
                  />
                ))}

                {chat.draftAssistant ? (
                  <div className="msg-block is-ai" id="typingIndicator">
                    <div className="bubble-ai rich-text draft-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                        {chat.draftAssistant}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : null}

                <div ref={bottomRef} />
              </>
            )}
          </div>
        </div>

        {chat.error ? <div className="chat-error">{chat.error}</div> : null}

        <ChatInput
          value={chat.input}
          modelName={selectedModel?.name || "选择模型"}
          modelColor={selectedModel?.color || "var(--brand-primary)"}
          showThinkingMode={isKimiModel}
          thinkingMode={chat.thinkingMode}
          disabled={!canSend}
          streaming={chat.streaming}
          onChange={(value) => {
            chat.clearError();
            chat.setInput(value);
          }}
          onThinkingModeChange={chat.setThinkingMode}
          onOpenModelModal={ui.openModelModal}
          onSend={() => void chat.sendMessage(withAuthRetry)}
          onStop={chat.stopStreaming}
        />

        <div className={ui.chatSidebarOpen ? "sidebar-overlay show" : "sidebar-overlay"} onClick={ui.closeChatSidebar} role="presentation" />
      </main>

      <ModelSelectorModal
        open={ui.modelModalOpen}
        models={chat.models}
        selectedModelId={chat.selectedModelId}
        search={ui.modelSearch}
        onSearchChange={ui.setModelSearch}
        onSelect={(modelId) => chat.setSelectedModel(modelId)}
        onClose={ui.closeModelModal}
      />
    </div>
  );
}
