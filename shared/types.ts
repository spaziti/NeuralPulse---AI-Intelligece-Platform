export interface User {
  id: string;
  email: string;
  fullName: string | null;
  isActive: boolean;
  createdAt: string;
}

export interface NewsArticle {
  id: string;
  title: string;
  url: string;
  source: string;
  content: string | null;
  summary: string | null;
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | null;
  sentimentScore: number | null;
  publishedAt: string;
  createdAt: string;
}

export interface AnalysisResult {
  articleId: string;
  summary: string;
  keyEntities: string[];
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  sentimentScore: number;
  topics: string[];
}

export interface IngestionLog {
  id: string;
  source: string;
  status: 'SUCCESS' | 'FAILED' | 'RUNNING';
  articlesCount: number;
  errorMessage: string | null;
  ranAt: string;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
  user: User;
}

export interface WebSocketNewsMessage {
  type: 'NEW_ARTICLE' | 'ARTICLE_UPDATED' | 'SYSTEM_STATUS';
  timestamp: string;
  payload: any;
}
