import { create } from "zustand";

interface UiStore {
  chatSidebarOpen: boolean;
  adminSidebarOpen: boolean;
  modelModalOpen: boolean;
  modelSearch: string;

  toggleChatSidebar: () => void;
  closeChatSidebar: () => void;
  toggleAdminSidebar: () => void;
  closeAdminSidebar: () => void;

  openModelModal: () => void;
  closeModelModal: () => void;
  setModelSearch: (value: string) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  chatSidebarOpen: false,
  adminSidebarOpen: false,
  modelModalOpen: false,
  modelSearch: "",

  toggleChatSidebar: () => set((state) => ({ chatSidebarOpen: !state.chatSidebarOpen })),
  closeChatSidebar: () => set({ chatSidebarOpen: false }),
  toggleAdminSidebar: () => set((state) => ({ adminSidebarOpen: !state.adminSidebarOpen })),
  closeAdminSidebar: () => set({ adminSidebarOpen: false }),

  openModelModal: () => set({ modelModalOpen: true }),
  closeModelModal: () => set({ modelModalOpen: false, modelSearch: "" }),
  setModelSearch: (value) => set({ modelSearch: value }),
}));
