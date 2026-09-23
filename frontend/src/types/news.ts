export type NewsTimeframe = "1h" | "24h" | "7d";
export type NewsMode = "events" | "articles";
export type InsightStatus = "pending" | "validated" | "unavailable";

export interface NewsFilters {
  category: string | null;
  source: string | null;
  timeframe: NewsTimeframe;
  /** Exact configured pair identifiers; an empty array requests all news. */
  pairs: string[];
}

export interface NewsViewState extends Omit<NewsFilters, "pairs"> {
  mode: NewsMode;
  pairScope: "configured" | "selected" | "all";
  selectedPairs: string[];
}

export const DEFAULT_NEWS_VIEW_STATE: NewsViewState = {
  mode: "events",
  category: null,
  source: null,
  timeframe: "24h",
  pairScope: "configured",
  selectedPairs: [],
};

export interface Article {
  id: string;
  sourceId: string;
  sourceName: string;
  url: string;
  headline: string;
  publishedAt: string;
  /** Publisher-provided text, never an AI-generated summary. */
  excerpt?: string;
  category: string;
  matchedAssets: string[];
  matchedPairs: string[];
}

export interface InsightStatement {
  text: string;
  articleIds: string[];
}

export interface Insight {
  eventId: string;
  generatedAt: string;
  model: string;
  factualSummary: InsightStatement[];
  marketContext: InsightStatement[];
  whatToWatch: InsightStatement[];
  /** Strength of supporting evidence, not probability of a price move. */
  confidence: "low" | "medium" | "high";
  validationStatus: "validated";
}

export interface NewsEvent {
  id: string;
  headline: string;
  category: string;
  firstReportedAt: string;
  updatedAt: string;
  matchedAssets: string[];
  matchedPairs: string[];
  /** Distinct publishers, not number of articles. */
  sourceCount: number;
  articles: Article[];
  insightStatus: InsightStatus;
  insight: Insight | null;
}

export interface NewsFeed<T> {
  items: T[];
  total: number;
  /** Last successful backend collection, not the time of this HTTP request. */
  lastSuccessfulRefreshAt: string | null;
  staleAfterSeconds: number;
}

export interface SourceStatus {
  id: string;
  name: string;
  status: "healthy" | "degraded" | "unavailable";
  lastSuccessfulRefreshAt: string | null;
  message?: string;
}

export interface NewsFilterOption {
  id: string;
  label: string;
}

export interface NewsStatus {
  checkedAt: string;
  sources: SourceStatus[];
  categories: NewsFilterOption[];
  ai: {
    status: "available" | "unavailable";
    message?: string;
  };
}
