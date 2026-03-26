import { useEffect, useMemo, useRef } from "react";
import { useShallow } from "zustand/react/shallow";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { ChatInput } from "../components/chat/ChatInput";
import { ChatMessage } from "../components/chat/ChatMessage";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ModelSelectorModal } from "../components/chat/ModelSelectorModal";
import { SettingsModal } from "../components/chat/SettingsModal";
import { WelcomeScreen } from "../components/chat/WelcomeScreen";
import { useChatStore } from "../stores/chatStore";
import { useUiStore } from "../stores/uiStore";

const REASONING_MODELS = new Set([
  "kimi-k2.5",
  "anthropic/claude-opus-4.6",
  "anthropic/claude-sonnet-4.6",
]);

export function ChatPage() {
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const stickToBottomRef = useRef(true);

  const chat = useChatStore(
    useShallow((state) => ({
      appConfig: state.appConfig,
      models: state.models,
      selectedModelId: state.selectedModelId,
      thinkingMode: state.thinkingMode,
      conversations: state.conversations,
      activeConversationId: state.activeConversationId,
      messages: state.messages,
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
      settingsModalOpen: state.settingsModalOpen,
      modelSearch: state.modelSearch,
      toggleChatSidebar: state.toggleChatSidebar,
      closeChatSidebar: state.closeChatSidebar,
      openModelModal: state.openModelModal,
      closeModelModal: state.closeModelModal,
      openSettingsModal: state.openSettingsModal,
      closeSettingsModal: state.closeSettingsModal,
      setModelSearch: state.setModelSearch,
    })),
  );

  useEffect(() => {
    chat.hydrateBase().catch((err) => {
      useChatStore.setState({ error: err instanceof Error ? err.message : "加载失败" });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    chat.hydrateMessages().catch((err) => {
      useChatStore.setState({ error: err instanceof Error ? err.message : "加载消息失败" });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat.activeConversationId]);

  useEffect(() => {
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        ui.closeModelModal();
        ui.closeSettingsModal();
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
  const supportsThinkingMode = selectedModel ? REASONING_MODELS.has(selectedModel.model) : false;
  const enabledProviderCount = chat.appConfig?.providers.filter((item) => item.enabled).length ?? 0;

  return (
    <div className={ui.chatSidebarOpen ? "app-layout chat-refined sidebar-open" : "app-layout chat-refined"}>
      <ChatSidebar
        username="本地用户"
        roleLabel="Direct"
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
          void chat.deleteConversation(id);
        }}
        onOpenSettings={ui.openSettingsModal}
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
              <span className={enabledProviderCount > 0 ? "status-dot status-ok" : "status-dot status-warn"} />
              {enabledProviderCount > 0 ? `本地直连 ${enabledProviderCount} 组` : "未配置 key"}
            </div>

            <button className="topbar-pill" type="button" onClick={ui.openSettingsModal} aria-label="打开本地设置">
              本地设置
            </button>

            <button className="icon-btn-ghost" type="button" onClick={() => void chat.hydrateBase()} aria-label="刷新">
              ↻
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
              />
            ) : (
              <>
                {chat.messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    canRegenerate={message.id === latestAssistantId}
                    onRegenerate={() => void chat.regenerateLastAssistant()}
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
          showThinkingMode={supportsThinkingMode}
          thinkingMode={chat.thinkingMode}
          disabled={!canSend}
          streaming={chat.streaming}
          onChange={(value) => {
            chat.clearError();
            chat.setInput(value);
          }}
          onThinkingModeChange={chat.setThinkingMode}
          onOpenModelModal={ui.openModelModal}
          onSend={() => void chat.sendMessage()}
          onStop={() => void chat.stopStreaming()}
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

      <SettingsModal open={ui.settingsModalOpen} config={chat.appConfig} onClose={ui.closeSettingsModal} />
    </div>
  );
}
