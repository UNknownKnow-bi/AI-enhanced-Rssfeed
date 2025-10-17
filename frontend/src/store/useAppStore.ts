import { create } from 'zustand';

interface AppStore {
  selectedSourceId: string | null;
  selectedArticleId: string | null;
  selectedCategory: string | null;
  selectedTags: string[];
  setSelectedSourceId: (id: string | null) => void;
  setSelectedArticleId: (id: string | null) => void;
  setSelectedCategory: (category: string | null) => void;
  setSelectedTags: (tags: string[]) => void;
  toggleTag: (tag: string) => void;
  clearTags: () => void;
}

export const useAppStore = create<AppStore>((set) => ({
  selectedSourceId: null,
  selectedArticleId: null,
  selectedCategory: null,
  selectedTags: [],

  setSelectedSourceId: (id) => set({
    selectedSourceId: id,
    selectedCategory: null,
    selectedArticleId: null,
    selectedTags: [] // Reset tags when changing source
  }),

  setSelectedArticleId: (id) => set({ selectedArticleId: id }),

  setSelectedCategory: (category) => set({
    selectedCategory: category,
    selectedSourceId: null,
    selectedArticleId: null,
    selectedTags: [] // Reset tags when changing category
  }),

  setSelectedTags: (tags) => set({ selectedTags: tags }),

  toggleTag: (tag) => set((state) => ({
    selectedTags: state.selectedTags.includes(tag)
      ? state.selectedTags.filter(t => t !== tag)
      : [...state.selectedTags, tag]
  })),

  clearTags: () => set({ selectedTags: [] }),
}));
