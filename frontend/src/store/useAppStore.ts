import { create } from 'zustand';

interface AppStore {
  selectedSourceId: string | null;
  selectedArticleId: string | null;
  selectedCategory: string | null;
  setSelectedSourceId: (id: string | null) => void;
  setSelectedArticleId: (id: string | null) => void;
  setSelectedCategory: (category: string | null) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  selectedSourceId: null,
  selectedArticleId: null,
  selectedCategory: null,
  setSelectedSourceId: (id) => set({ selectedSourceId: id, selectedCategory: null, selectedArticleId: null }),
  setSelectedArticleId: (id) => set({ selectedArticleId: id }),
  setSelectedCategory: (category) => set({ selectedCategory: category, selectedSourceId: null, selectedArticleId: null }),
}));
