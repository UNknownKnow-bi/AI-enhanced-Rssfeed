import { create } from 'zustand';

interface AppStore {
  selectedSourceId: string | null;
  selectedArticleId: string | null;
  setSelectedSourceId: (id: string | null) => void;
  setSelectedArticleId: (id: string | null) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  selectedSourceId: null,
  selectedArticleId: null,
  setSelectedSourceId: (id) => set({ selectedSourceId: id, selectedArticleId: null }),
  setSelectedArticleId: (id) => set({ selectedArticleId: id }),
}));
