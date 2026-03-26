import { create } from "zustand";

interface UiStore {
  chatSidebarOpen: boolean;
  modelModalOpen: boolean;
  settingsModalOpen: boolean;
  modelSearch: string;

  toggleChatSidebar: () => void;
  closeChatSidebar: () => void;
  openModelModal: () => void;
  closeModelModal: () => void;
  openSettingsModal: () => void;
  closeSettingsModal: () => void;
  setModelSearch: (value: string) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  chatSidebarOpen: false,
  modelModalOpen: false,
  settingsModalOpen: false,
  modelSearch: "",

  toggleChatSidebar: () => set((state) => ({ chatSidebarOpen: !state.chatSidebarOpen })),
  closeChatSidebar: () => set({ chatSidebarOpen: false }),
  openModelModal: () => set({ modelModalOpen: true }),
  closeModelModal: () => set({ modelModalOpen: false, modelSearch: "" }),
  openSettingsModal: () => set({ settingsModalOpen: true }),
  closeSettingsModal: () => set({ settingsModalOpen: false }),
  setModelSearch: (value) => set({ modelSearch: value }),
}));
