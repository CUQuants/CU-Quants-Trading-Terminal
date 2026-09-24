import type { ReactNode } from "react";
import type { Article, Insight, InsightStatement, NewsEvent } from "../../types/news";

export function NewsTime({ value, now }: { value: string | null; now: number }) {
  if (!value) return <span>Never</span>;
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return <span>Unknown time</span>;
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  const age = seconds < 60 ? "Just now"
    : seconds < 3600 ? `${Math.floor(seconds / 60)}m ago`
    : seconds < 86400 ? `${Math.floor(seconds / 3600)}h ago`
    : `${Math.floor(seconds / 86400)}d ago`;
  return <time dateTime={value} title={new Date(timestamp).toLocaleString()}>{age}</time>;
}

function SourceLink({ article, children }: { article: Article; children?: ReactNode }) {
  // Treat all publisher URLs as untrusted, even when the rest of a report is valid.
  let safe = false;
  try {
    const url = new URL(article.url);
    safe = url.protocol === "https:" || url.protocol === "http:";
  } catch {
    safe = false;
  }
  if (!safe) return <span>{children ?? article.headline} <span className="text-amber-300">(link unavailable)</span></span>;
  return (
    <a href={article.url} target="_blank" rel="noopener noreferrer" className="text-sky-300 hover:text-sky-200 underline decoration-sky-300/30 underline-offset-4 break-words">
      {children ?? article.headline}<span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

function Matches({ assets, pairs }: { assets: string[]; pairs: string[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/50">
      <span>Assets: <span className="text-white/75">{assets.length ? assets.join(", ") : "None matched"}</span></span>
      <span>Pairs: <span className="text-white/75">{pairs.length ? pairs.join(", ") : "None matched"}</span></span>
    </div>
  );
}

function InsightSection({ title, statements, articles }: {
  title: string;
  statements: InsightStatement[];
  articles: Article[];
}) {
  return (
    <section className="space-y-2">
      <h4 className="text-xs font-semibold text-white/75">{title}</h4>
      <ul className="space-y-2 text-sm leading-relaxed text-white/65">
        {statements.map((statement, index) => (
          <li key={index}>
            <p className="whitespace-pre-line">{statement.text}</p>
            <div className="flex flex-wrap gap-x-3 text-xs mt-1">
              {[...new Set(statement.articleIds)].map((id) => {
                const article = articles.find((item) => item.id === id);
                return article ? <SourceLink key={id} article={article}>{article.sourceName}: {article.headline}</SourceLink> : null;
              })}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function InsightCard({ insight, articles, now }: { insight: Insight; articles: Article[]; now: number }) {
  return (
    <section aria-label="Claude-generated insight" className="rounded-lg border border-sky-400/20 bg-sky-400/[0.04] p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-sky-200">Claude-generated insight</h3>
        <span className="text-xs text-white/50">Evidence confidence: <span className="capitalize text-white/75">{insight.confidence}</span></span>
      </div>
      <p className="text-xs text-white/40">Confidence describes source support, not the probability of a price move. AI interpretation may be incorrect.</p>
      <InsightSection title="Factual summary · AI-generated from sources" statements={insight.factualSummary} articles={articles} />
      <div className="border-t border-sky-400/15 pt-4 space-y-4">
        <p className="text-[10px] uppercase tracking-wider text-sky-200/60">Interpretation · informational only</p>
        <InsightSection title="Market context" statements={insight.marketContext} articles={articles} />
        <InsightSection title="What to watch" statements={insight.whatToWatch} articles={articles} />
      </div>
      <p className="text-[11px] text-white/40">{insight.model} · Generated <NewsTime value={insight.generatedAt} now={now} /> · Not a trading recommendation</p>
    </section>
  );
}

export function ArticleCard({ article, now, categoryLabel }: { article: Article; now: number; categoryLabel: string }) {
  return (
    <article className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-white/50">
        <span className="rounded border border-white/10 px-2 py-0.5">{categoryLabel}</span>
        <span>{article.sourceName}</span>
        <span>·</span>
        <NewsTime value={article.publishedAt} now={now} />
      </div>
      <h2 className="text-base font-semibold leading-relaxed"><SourceLink article={article} /></h2>
      <Matches assets={article.matchedAssets} pairs={article.matchedPairs} />
      {article.excerpt && (
        <div className="border-t border-white/10 pt-3">
          <p className="text-[10px] uppercase tracking-wider text-white/40 mb-1">Source-reported excerpt</p>
          <p className="text-sm leading-relaxed text-white/70 whitespace-pre-line">{article.excerpt}</p>
        </div>
      )}
    </article>
  );
}

export function NewsEventCard({ event, now, categoryLabel }: { event: NewsEvent; now: number; categoryLabel: string }) {
  return (
    <article className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-white/50">
        <span className="rounded border border-white/10 px-2 py-0.5">{categoryLabel}</span>
        <span>{event.sourceCount} {event.sourceCount === 1 ? "source" : "sources"}</span>
        <span>·</span>
        <span>Updated <NewsTime value={event.updatedAt} now={now} /></span>
      </div>
      <div>
        <h2 className="text-base font-semibold leading-relaxed text-white/90">{event.headline}</h2>
        <p className="mt-1 text-xs text-white/40">First reported <NewsTime value={event.firstReportedAt} now={now} /></p>
      </div>
      <Matches assets={event.matchedAssets} pairs={event.matchedPairs} />
      <details className="rounded-lg border border-white/10 bg-black/20">
        <summary className="cursor-pointer p-3 text-sm text-white/75">Source reports · {event.articles.length} original {event.articles.length === 1 ? "article" : "articles"}</summary>
        <ul className="px-3 pb-3 space-y-4">
          {event.articles.map((article) => (
            <li key={article.id} className="border-t border-white/10 pt-3 text-sm">
              <p className="mb-1 text-xs text-white/40">{article.sourceName} · <NewsTime value={article.publishedAt} now={now} /></p>
              <SourceLink article={article} />
              {article.excerpt && <p className="mt-2 text-white/65 leading-relaxed whitespace-pre-line">{article.excerpt}</p>}
            </li>
          ))}
        </ul>
      </details>
      {event.insightStatus === "validated" && event.insight ? (
        <InsightCard insight={event.insight} articles={event.articles} now={now} />
      ) : (
        <p className="rounded-lg border border-white/10 p-3 text-xs text-white/50">
          {event.insightStatus === "pending" ? "Claude insight is being prepared. Source reports are available above." : "Claude insight unavailable. Source reports are available above."}
        </p>
      )}
    </article>
  );
}
