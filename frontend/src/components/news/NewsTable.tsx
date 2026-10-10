import type { Article, NewsEvent } from "../../types/news";
import { NewsTime, SourceLink } from "./NewsCards";

interface Props {
  items: (Article | NewsEvent)[];
  now: number;
  categoryLabel: (id: string) => string;
}

const LINK_WORD_LIMIT = 24;
const AGE_FADE_MS = 60 * 60 * 1000;
const QUANTS_BLUE = [47, 113, 200];

function previewText(text: string) {
  const words = text.trim().split(/\s+/);
  return words.length > LINK_WORD_LIMIT ? `${words.slice(0, LINK_WORD_LIMIT).join(" ")}…` : words.join(" ");
}

function postedColor(postedAt: string, now: number) {
  const timestamp = Date.parse(postedAt);
  const fade = Number.isFinite(timestamp) ? Math.min(1, Math.max(0, now - timestamp) / AGE_FADE_MS) : 1;
  const channels = QUANTS_BLUE.map((channel) => Math.round(channel + (148 - channel) * fade));
  return `rgb(${channels.join(", ")})`;
}

export function NewsTable({ items, now, categoryLabel }: Props) {
  return (
    <div className="w-full min-w-0">
      <table className="w-full table-fixed text-left text-[clamp(8px,1.1vw,14px)] [&_td]:px-[clamp(2px,0.6vw,16px)] [&_th]:px-[clamp(2px,0.6vw,16px)] [&_td]:text-inherit [&_th]:text-inherit [&_th]:truncate">
        <caption className="sr-only">News feed. Asset price changes are not connected yet.</caption>
        <colgroup>
          <col className="w-[11%] lg:w-28" />
          <col className="w-[14%] lg:w-40" />
          <col className="w-[14%] lg:w-36" />
          <col className="w-[11%] lg:w-32" />
          <col className="w-[14%] lg:w-40" />
          <col />
        </colgroup>
        <thead className="bg-white/[0.07] text-xs text-white/60">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">Posted</th>
            <th scope="col" className="px-4 py-3 font-medium">Asset name</th>
            <th scope="col" className="px-4 py-3 font-medium" title="Pairs">Pairs</th>
            <th scope="col" className="px-4 py-3 text-right font-medium" title="Price change">Price change</th>
            <th scope="col" className="px-4 py-3 font-medium" title="Category">Category</th>
            <th scope="col" className="px-4 py-3 font-medium">Excerpt / headline</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {items.map((item) => {
            const event = "articles" in item ? item : null;
            const article = event
              ? event.articles.find((source) => source.excerpt?.trim()) ?? event.articles[0]
              : item as Article;
            const linkText = article?.excerpt?.trim() || item.headline;
            const postedAt = event ? event.firstReportedAt : (item as Article).publishedAt;
            return (
              <tr key={item.id} className="align-top even:bg-white/[0.02] hover:bg-white/[0.05]">
                <td className="px-4 py-3 truncate transition-colors duration-1000 motion-reduce:transition-none"
                  style={{ color: postedColor(postedAt, now) }}>
                  <NewsTime value={postedAt} now={now} />
                </td>
                <th scope="row" className="px-4 py-3 font-medium text-white/85 truncate" title={item.matchedAssets.join(", ") || "General market"}>
                  {item.matchedAssets.length ? item.matchedAssets.join(", ") : "General market"}
                </th>
                <td className="px-4 py-3 text-white/60 truncate" title={item.matchedPairs.join(", ")}>
                  {item.matchedPairs.length ? item.matchedPairs.join(", ") : "—"}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-white/35 truncate">
                  <span aria-label="Asset price change not connected" title="Asset price change not connected">—</span>
                </td>
                <td className="px-4 py-3 text-white/60 truncate" title={categoryLabel(item.category)}>{categoryLabel(item.category)}</td>
                <td className="px-4 py-3">
                  <div className="relative font-medium leading-snug truncate" title={linkText}>
                    {article ? <SourceLink article={article}>{previewText(linkText)}</SourceLink> : <span>{previewText(linkText)}</span>}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
