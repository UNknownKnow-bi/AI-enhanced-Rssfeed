import { create } from 'zustand';

interface AppStore {
  selectedSourceId: string | null;
  selectedArticleId: string | null;
  selectedCategory: string | null;
  selectedTags: string[];
  selectedView: 'favorites' | 'trash' | null;
  setSelectedSourceId: (id: string | null) => void;
  setSelectedArticleId: (id: string | null) => void;
  setSelectedCategory: (category: string | null) => void;
  setSelectedTags: (tags: string[]) => void;
  setSelectedView: (view: 'favorites' | 'trash' | null) => void;
  toggleTag: (tag: string) => void;
  clearTags: () => void;
}

export const useAppStore = create<AppStore>((set) => ({
  selectedSourceId: null,
  selectedArticleId: null,
  selectedCategory: null,
  selectedTags: [],
  selectedView: null,

  setSelectedSourceId: (id) => set({
    selectedSourceId: id,
    selectedCategory: null,
    selectedArticleId: null,
    selectedTags: [], // Reset tags when changing source
    selectedView: null // Reset view when changing source
  }),

  setSelectedArticleId: (id) => set({ selectedArticleId: id }),

  setSelectedCategory: (category) => set({
    selectedCategory: category,
    selectedSourceId: null,
    selectedArticleId: null,
    selectedTags: [], // Reset tags when changing category
    selectedView: null // Reset view when changing category
  }),

  setSelectedTags: (tags) => set({ selectedTags: tags }),

  setSelectedView: (view) => set({
    selectedView: view,
    selectedSourceId: null,
    selectedCategory: null,
    selectedArticleId: null,
    selectedTags: [] // Reset tags when changing view
  }),

  toggleTag: (tag) => set((state) => ({
    selectedTags: state.selectedTags.includes(tag)
      ? state.selectedTags.filter(t => t !== tag)
      : [...state.selectedTags, tag]
  })),

  clearTags: () => set({ selectedTags: [] }),
}));
