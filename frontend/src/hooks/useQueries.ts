import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../lib/api';
import type { AddSourceRequest, UpdateSourceRequest } from '../types';

// Query keys
export const queryKeys = {
  sources: ['sources'] as const,
  articles: (sourceId?: string) => ['articles', sourceId] as const,
  article: (articleId: string) => ['article', articleId] as const,
};

// RSS Sources
export const useRSSSources = () => {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: api.fetchRSSSources,
    refetchInterval: 60000, // Refetch every minute
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
    // On success, invalidate to get fresh data
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
    // On error, roll back to the previous value
    onError: (err, variables, context) => {
      if (context?.previousSources) {
        queryClient.setQueryData(queryKeys.sources, context.previousSources);
      }
    },
    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
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

export const useArticles = (sourceId?: string) => {
  return useInfiniteQuery({
    queryKey: queryKeys.articles(sourceId),
    queryFn: ({ pageParam = 0 }) => api.fetchArticles(sourceId, ARTICLES_PER_PAGE, pageParam),
    getNextPageParam: (lastPage, allPages) => {
      // If the last page has fewer articles than the page size, we've reached the end
      if (lastPage.length < ARTICLES_PER_PAGE) {
        return undefined;
      }
      // Otherwise, return the offset for the next page
      return allPages.length * ARTICLES_PER_PAGE;
    },
    refetchInterval: 60000, // Refetch every minute
    initialPageParam: 0,
  });
};

export const useArticle = (articleId: string | null) => {
  return useQuery({
    queryKey: queryKeys.article(articleId!),
    queryFn: () => api.fetchArticle(articleId!),
    enabled: !!articleId,
  });
};

export const useMarkAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (articleId: string) => api.markArticleAsRead(articleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });
};
