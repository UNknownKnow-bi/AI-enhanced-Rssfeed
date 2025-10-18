import axios from 'axios';
import type { RSSSource, Article, RSSValidateRequest, RSSValidateResponse, AddSourceRequest, UpdateSourceRequest } from '../types';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// RSS Source APIs
export const validateRSSUrl = async (url: string): Promise<RSSValidateResponse> => {
  const response = await api.post<RSSValidateResponse>('/api/rss/validate', { url });
  return response.data;
};

export const createRSSSource = async (data: AddSourceRequest): Promise<RSSSource> => {
  const response = await api.post<RSSSource>('/api/sources', data);
  return response.data;
};

export const fetchRSSSources = async (): Promise<RSSSource[]> => {
  const response = await api.get<RSSSource[]>('/api/sources');
  return response.data;
};

export const deleteRSSSource = async (sourceId: string): Promise<void> => {
  await api.delete(`/api/sources/${sourceId}`);
};

export const updateRSSSource = async (sourceId: string, data: UpdateSourceRequest): Promise<RSSSource> => {
  const response = await api.patch<RSSSource>(`/api/sources/${sourceId}`, data);
  return response.data;
};

// Article APIs
export const fetchArticles = async (
  sourceId?: string,
  category?: string,
  tags?: string[],
  isRead?: boolean,
  isFavorite?: boolean,
  isTrashed?: boolean,
  limit: number = 50,
  offset: number = 0
): Promise<Article[]> => {
  const params: Record<string, any> = { limit, offset };
  if (sourceId) {
    params.source_id = sourceId;
  } else if (category) {
    params.category = category;
  }
  // Add tags parameter (comma-separated)
  if (tags && tags.length > 0) {
    params.tags = tags.join(',');
  }
  // Add status filters
  if (isRead !== undefined) {
    params.is_read = isRead;
  }
  if (isFavorite !== undefined) {
    params.is_favorite = isFavorite;
  }
  if (isTrashed !== undefined) {
    params.is_trashed = isTrashed;
  }
  const response = await api.get<Article[]>('/api/articles', { params });
  return response.data;
};

export const fetchArticle = async (articleId: string): Promise<Article> => {
  const response = await api.get<Article>(`/api/articles/${articleId}`);
  return response.data;
};

export const markArticleAsRead = async (articleId: string, isRead: boolean): Promise<Article> => {
  const response = await api.patch<Article>(`/api/articles/${articleId}/read`, { is_read: isRead });
  return response.data;
};

export const toggleArticleFavorite = async (articleId: string, isFavorite: boolean): Promise<Article> => {
  const response = await api.patch<Article>(`/api/articles/${articleId}/favorite`, { is_favorite: isFavorite });
  return response.data;
};

export const trashArticle = async (articleId: string): Promise<void> => {
  await api.post(`/api/articles/${articleId}/trash`);
};

export const restoreArticle = async (articleId: string): Promise<Article> => {
  const response = await api.post<Article>(`/api/articles/${articleId}/restore`);
  return response.data;
};

export const emptyTrash = async (): Promise<{ message: string; count: number }> => {
  const response = await api.delete<{ message: string; count: number }>('/api/articles/trash', {
    data: { confirm: true }
  });
  return response.data;
};

export const getArticleCounts = async (): Promise<{ unread: number; favorite: number; trashed: number }> => {
  const response = await api.get<{ unread: number; favorite: number; trashed: number }>('/api/articles/counts');
  return response.data;
};

export const fetchAvailableTags = async (
  sourceId?: string,
  category?: string
): Promise<string[]> => {
  const params: Record<string, any> = {};
  if (sourceId) {
    params.source_id = sourceId;
  } else if (category) {
    params.category = category;
  }
  const response = await api.get<string[]>('/api/articles/tags', { params });
  return response.data;
};
