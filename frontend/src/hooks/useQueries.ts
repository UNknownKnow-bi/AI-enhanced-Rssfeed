import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../lib/api';
import type { AddSourceRequest, UpdateSourceRequest } from '../types';

// Query keys
export const queryKeys = {
  sources: ['sources'] as const,
  articles: (sourceId?: string, category?: string, tags?: string[], isRead?: boolean, isFavorite?: boolean, isTrashed?: boolean) => {
    // Sort tags alphabetically for consistent cache keys
    const sortedTags = tags && tags.length > 0 ? [...tags].sort() : undefined;
    return ['articles', sourceId, category, sortedTags, isRead, isFavorite, isTrashed] as const;
  },
  article: (articleId: string) => ['article', articleId] as const,
  availableTags: (sourceId?: string, category?: string) => ['availableTags', sourceId, category] as const,
};

// RSS Sources
export const useRSSSources = () => {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: api.fetchRSSSources,
    staleTime: 2 * 60 * 1000, // 2 minutes - sources don't change often
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes instead of 1
  });
};

export const useCreateSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AddSourceRequest) => api.createRSSSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    },
  });
};

export const useUpdateSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: UpdateSourceRequest }) =>
      api.updateRSSSource(sourceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    },
  });
};

export const useDeleteSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sourceId: string) => api.deleteRSSSource(sourceId),
    // Optimistic update
    onMutate: async (sourceId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.sources });

      // Snapshot the previous value
      const previousSources = queryClient.getQueryData(queryKeys.sources);

      // Optimistically update to remove the source
      queryClient.setQueryData(queryKeys.sources, (old: any) =>
        old?.filter((source: any) => source.id !== sourceId)
      );

      // Return a context object with the snapshotted value
      return { previousSources };
    },
    // On success, only invalidate affected queries
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      // Only invalidate articles queries (don't refetch all at once)
      queryClient.invalidateQueries({
        queryKey: ['articles'],
        refetchType: 'none' // Mark as stale but don't refetch immediately
      });
    },
    // On error, roll back to the previous value
    onError: (_err, _variables, context) => {
      if (context?.previousSources) {
        queryClient.setQueryData(queryKeys.sources, context.previousSources);
      }
    },
  });
};

export const useValidateURL = () => {
  return useMutation({
    mutationFn: (url: string) => api.validateRSSUrl(url),
  });
};

// Articles - Infinite Query for Pagination
const ARTICLES_PER_PAGE = 50;

export const useArticles = (
  sourceId?: string,
  category?: string,
  tags?: string[],
  isRead?: boolean,
  isFavorite?: boolean,
  isTrashed?: boolean
) => {
  return useInfiniteQuery({
    queryKey: queryKeys.articles(sourceId, category, tags, isRead, isFavorite, isTrashed),
    queryFn: ({ pageParam = 0 }) =>
      api.fetchArticles(sourceId, category, tags, isRead, isFavorite, isTrashed, ARTICLES_PER_PAGE, pageParam),
    getNextPageParam: (lastPage, allPages) => {
      // If the last page has fewer articles than the page size, we've reached the end
      if (lastPage.length < ARTICLES_PER_PAGE) {
        return undefined;
      }
      // Otherwise, return the offset for the next page
      return allPages.length * ARTICLES_PER_PAGE;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes - articles don't update that frequently
    refetchInterval: 3 * 60 * 1000, // Refetch every 3 minutes instead of 1
    initialPageParam: 0,
  });
};

export const useAvailableTags = (sourceId?: string, category?: string) => {
  return useQuery({
    queryKey: queryKeys.availableTags(sourceId, category),
    queryFn: () => api.fetchAvailableTags(sourceId, category),
    staleTime: 3 * 60 * 1000, // 3 minutes - tags change rarely
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
};

export const useArticle = (articleId: string | null) => {
  return useQuery({
    queryKey: queryKeys.article(articleId!),
    queryFn: () => api.fetchArticle(articleId!),
    enabled: !!articleId,
    staleTime: 5 * 60 * 1000, // 5 minutes - individual articles rarely change
  });
};

export const useMarkAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ articleId, isRead }: { articleId: string; isRead: boolean }) =>
      api.markArticleAsRead(articleId, isRead),
    onSuccess: (updatedArticle) => {
      // Update the specific article in cache
      queryClient.setQueryData(queryKeys.article(updatedArticle.id), updatedArticle);
      // Invalidate articles list to refresh counts
      queryClient.invalidateQueries({
        queryKey: ['articles'],
        refetchType: 'none'
      });
    },
  });
};

export const useToggleFavorite = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ articleId, isFavorite }: { articleId: string; isFavorite: boolean }) =>
      api.toggleArticleFavorite(articleId, isFavorite),
    // Optimistic update
    onMutate: async ({ articleId, isFavorite }) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: queryKeys.article(articleId) });

      // Snapshot previous value
      const previousArticle = queryClient.getQueryData(queryKeys.article(articleId));

      // Optimistically update
      queryClient.setQueryData(queryKeys.article(articleId), (old: any) =>
        old ? { ...old, is_favorite: isFavorite } : old
      );

      return { previousArticle };
    },
    onSuccess: (updatedArticle) => {
      // Update with real data from server
      queryClient.setQueryData(queryKeys.article(updatedArticle.id), updatedArticle);
    },
    onError: (_err, { articleId }, context) => {
      // Rollback on error
      if (context?.previousArticle) {
        queryClient.setQueryData(queryKeys.article(articleId), context.previousArticle);
      }
    },
    onSettled: () => {
      // Always invalidate articles list
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });
};

export const useTrashArticle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (articleId: string) => api.trashArticle(articleId),
    onSuccess: (_, articleId) => {
      // Invalidate both the specific article and articles list
      queryClient.invalidateQueries({ queryKey: queryKeys.article(articleId) });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });
};

export const useRestoreArticle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (articleId: string) => api.restoreArticle(articleId),
    onSuccess: (updatedArticle) => {
      // Update cache with restored article
      queryClient.setQueryData(queryKeys.article(updatedArticle.id), updatedArticle);
      // Invalidate articles list
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });
};

export const useEmptyTrash = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.emptyTrash(),
    onSuccess: () => {
      // Invalidate all articles queries
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });
};

export const useArticleCounts = () => {
  return useQuery({
    queryKey: ['articleCounts'],
    queryFn: api.getArticleCounts,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Refetch every minute
  });
};

// Category Rename - Batch update all sources in a category
export const useRenameCategoryMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      newCategory,
      sourceIds,
    }: {
      oldCategory: string;
      newCategory: string;
      sourceIds: string[];
    }) => {
      // Batch update all sources with retry logic
      const updateSource = async (sourceId: string, retryCount = 0): Promise<any> => {
        try {
          return await api.updateRSSSource(sourceId, { category: newCategory });
        } catch (error) {
          // Retry once if failed
          if (retryCount < 1) {
            return await updateSource(sourceId, retryCount + 1);
          }
          throw error;
        }
      };

      const results = await Promise.allSettled(
        sourceIds.map((id) => updateSource(id))
      );

      // Check for failures
      const failures = results.filter((r) => r.status === 'rejected');
      if (failures.length > 0) {
        throw new Error(`${failures.length} 个源更新失败`);
      }

      return results;
    },

    // Optimistic update
    onMutate: async ({ newCategory, sourceIds }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.sources });

      const previousSources = queryClient.getQueryData(queryKeys.sources);

      // Optimistically update cache
      queryClient.setQueryData(queryKeys.sources, (old: any) =>
        old?.map((source: any) =>
          sourceIds.includes(source.id)
            ? { ...source, category: newCategory }
            : source
        )
      );

      return { previousSources };
    },

    // Rollback on error
    onError: (_err, _variables, context) => {
      if (context?.previousSources) {
        queryClient.setQueryData(queryKeys.sources, context.previousSources);
      }
    },

    // Invalidate on success
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      // Mark articles as stale but don't refetch immediately
      queryClient.invalidateQueries({
        queryKey: ['articles'],
        refetchType: 'none'
      });
    },
  });
};
