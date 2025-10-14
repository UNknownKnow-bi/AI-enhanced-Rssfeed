import axios from 'axios';
import type { RSSSource, Article, RSSValidateRequest, RSSValidateResponse, AddSourceRequest } from '../types';

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

// Article APIs
export const fetchArticles = async (sourceId?: string): Promise<Article[]> => {
  const params = sourceId ? { source_id: sourceId } : {};
  const response = await api.get<Article[]>('/api/articles', { params });
  return response.data;
};

export const fetchArticle = async (articleId: string): Promise<Article> => {
  const response = await api.get<Article>(`/api/articles/${articleId}`);
  return response.data;
};

export const markArticleAsRead = async (articleId: string): Promise<void> => {
  await api.patch(`/api/articles/${articleId}/read`);
};
