import type {
  Article,
  Insight,
  NewsEvent,
  NewsFeed,
  NewsFilters,
  NewsStatus,
} from "../types/news";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const NEWS_LIMIT = 100;

export class NewsApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "NewsApiError";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isDate(value: unknown): value is string {
  return isString(value) && Number.isFinite(Date.parse(value));
}

function isStrings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function isOptionalText(value: unknown): boolean {
  return value === undefined || typeof value === "string";
}

function isArticle(value: unknown): value is Article {
  if (!isRecord(value)) return false;
  return [value.id, value.sourceId, value.sourceName, value.url, value.headline, value.category].every(isString)
    && isDate(value.publishedAt)
    && isOptionalText(value.excerpt)
    && isStrings(value.matchedAssets)
    && isStrings(value.matchedPairs);
}

function isInsight(value: unknown, eventId: string, articles: Article[]): value is Insight {
  if (!isRecord(value) || value.validationStatus !== "validated" || value.eventId !== eventId) return false;
  const articleIds = new Set(articles.map((article) => article.id));
  const hasStatements = (statements: unknown) => Array.isArray(statements)
    && statements.length > 0
    && statements.every((statement) => isRecord(statement)
      && isString(statement.text)
      && isStrings(statement.articleIds)
      && statement.articleIds.length > 0
      && statement.articleIds.every((id) => articleIds.has(id)));
  return isDate(value.generatedAt)
    && isString(value.model)
    && ["low", "medium", "high"].includes(String(value.confidence))
    && hasStatements(value.factualSummary)
    && hasStatements(value.marketContext)
    && hasStatements(value.whatToWatch);
}

function parseEvent(value: unknown): NewsEvent {
  if (!isRecord(value)
    || ![value.id, value.headline, value.category].every(isString)
    || !isDate(value.firstReportedAt) || !isDate(value.updatedAt)
    || !isStrings(value.matchedAssets) || !isStrings(value.matchedPairs)
    || !Array.isArray(value.articles) || value.articles.length === 0 || !value.articles.every(isArticle)
    || !Number.isInteger(value.sourceCount)
    || value.sourceCount !== new Set(value.articles.map((article) => article.sourceId)).size) {
    throw new NewsApiError("The news service returned an unsupported event format.", 0);
  }

  // A bad or unvalidated insight must not prevent displaying its source reports.
  const validated = value.insightStatus === "validated"
    && isInsight(value.insight, value.id as string, value.articles);
  return {
    ...value,
    insightStatus: validated ? "validated" : value.insightStatus === "pending" ? "pending" : "unavailable",
    insight: validated ? value.insight : null,
  } as unknown as NewsEvent;
}

function parseFeed<T>(value: unknown, parseItem: (item: unknown) => T): NewsFeed<T> {
  if (!isRecord(value) || !Array.isArray(value.items)
    || typeof value.total !== "number" || !Number.isInteger(value.total) || value.total < value.items.length
    || !(value.lastSuccessfulRefreshAt === null || isDate(value.lastSuccessfulRefreshAt))
    || typeof value.staleAfterSeconds !== "number" || !Number.isFinite(value.staleAfterSeconds) || value.staleAfterSeconds <= 0) {
    throw new NewsApiError("The news service returned an unsupported feed format.", 0);
  }
  return {
    items: value.items.map(parseItem),
    total: value.total,
    lastSuccessfulRefreshAt: value.lastSuccessfulRefreshAt,
    staleAfterSeconds: value.staleAfterSeconds,
  };
}

async function request(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(`${API_BASE}${path}`, { signal });
  if (!response.ok) {
    const message = response.status === 404 || response.status === 501
      ? "News is not available from the connected service yet."
      : `Unable to refresh news (HTTP ${response.status}).`;
    throw new NewsApiError(message, response.status);
  }
  try {
    return await response.json();
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new NewsApiError("The news service returned an unreadable response.", 0);
  }
}

function queryString(filters: NewsFilters): string {
  const params = new URLSearchParams({ timeframe: filters.timeframe, limit: String(NEWS_LIMIT) });
  if (filters.category) params.set("category", filters.category);
  if (filters.source) params.set("source", filters.source);
  for (const pair of [...new Set(filters.pairs)].sort()) params.append("pair", pair);
  return params.toString();
}

export async function fetchNews(filters: NewsFilters, signal?: AbortSignal): Promise<NewsFeed<Article>> {
  return parseFeed(await request(`/news?${queryString(filters)}`, signal), (item) => {
    if (!isArticle(item)) throw new NewsApiError("The news service returned an unsupported article format.", 0);
    return item;
  });
}

export async function fetchNewsEvents(filters: NewsFilters, signal?: AbortSignal): Promise<NewsFeed<NewsEvent>> {
  return parseFeed(await request(`/news/events?${queryString(filters)}`, signal), parseEvent);
}

export async function fetchNewsStatus(signal?: AbortSignal): Promise<NewsStatus> {
  const value = await request("/news/status", signal);
  if (!isRecord(value) || !isDate(value.checkedAt)
    || !Array.isArray(value.sources) || !value.sources.every((source) => isRecord(source)
      && isString(source.id) && isString(source.name)
      && ["healthy", "degraded", "unavailable"].includes(String(source.status))
      && (source.lastSuccessfulRefreshAt === null || isDate(source.lastSuccessfulRefreshAt))
      && isOptionalText(source.message))
    || !Array.isArray(value.categories) || !value.categories.every((category) => isRecord(category)
      && isString(category.id) && isString(category.label))
    || !isRecord(value.ai) || !["available", "unavailable"].includes(String(value.ai.status))
    || !isOptionalText(value.ai.message)) {
    throw new NewsApiError("News provider status is unavailable: unsupported response format.", 0);
  }
  return value as unknown as NewsStatus;
}
