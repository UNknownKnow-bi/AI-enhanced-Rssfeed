export interface RSSSource {
  id: string;
  user_id: string;
  url: string;
  title: string;
  description?: string;
  icon: string;
  category: string;
  unread_count: number;
  created_at: string;
  last_fetched?: string;
}

export interface Article {
  id: string;
  source_id: string;
  guid: string;
  title: string;
  link: string;
  description?: string;
  content?: string;
  cover_image?: string;
  pub_date?: string;
  is_read: boolean;
  created_at: string;
  source_name: string;
  source_icon: string;
}

export interface RSSValidateRequest {
  url: string;
}

export interface RSSValidateResponse {
  valid: boolean;
  title?: string;
  description?: string;
  error?: string;
}

export interface AddSourceRequest {
  url: string;
  title: string;
  category: string;
}

export interface UpdateSourceRequest {
  title?: string;
  icon?: string;
  category?: string;
}
