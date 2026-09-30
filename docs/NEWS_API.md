# News frontend and backend contract

The News view consumes a cached backend feed. This change implements the frontend
only; the current backend has no `/news` routes. Until those routes are provided,
the page displays **News unavailable**. There is no mock data or demo mode.

The TypeScript contract is in
[`frontend/src/types/news.ts`](../frontend/src/types/news.ts). Response field names
are camelCase. IDs are stable strings, timestamps are UTC ISO 8601 strings, and
original article URLs must be absolute HTTP(S) URLs. Text fields are plain text,
not HTML or Markdown. Optional text fields should be omitted when unavailable.

## Endpoints

All requests use `VITE_API_URL`, defaulting to `http://localhost:8000`.

| GET endpoint | Response | Purpose |
| --- | --- | --- |
| `/news` | `NewsFeed<Article>` | Individual source reports, newest publication first. |
| `/news/events` | `NewsFeed<NewsEvent>` | Grouped events, newest update first, with complete supporting articles and optional validated insight. |
| `/news/status` | `NewsStatus` | Provider health, source/category filter options, and availability of new Claude insights. |

The GET routes read cached results. They must not trigger provider collection or
Claude generation for each browser request. Feed collection, caching, event
grouping, asset matching, and Claude processing are separate backend work.

### Feed query parameters

| Parameter | Values and behavior |
| --- | --- |
| `category` | Optional category ID; omitted means all categories. |
| `source` | Optional source ID; omitted means all sources. |
| `timeframe` | `1h`, `24h`, or `7d`; the frontend defaults to `24h`. Evaluate relative to the server's current time. |
| `pair` | Repeated exact configured pair strings, such as `pair=BTC%2FUSD&pair=ETH%2FUSD`. Omitted means all news. |
| `limit` | Frontend requests `100`. Return at most that many items. |

Different filter dimensions combine with AND. Multiple requested pairs combine
with OR. Match articles by `publishedAt`, events by `updatedAt`. Matching belongs
entirely to the backend, including ticker aliases, currency differences, and asset
relevance. The browser sorts and deduplicates pair strings but never translates
them. Matching is asset/pair-based, not restricted to a trading exchange.

An event matches a source when at least one supporting article has that source
ID. Return the full supporting article list even when source/timeframe filters
are applied. Group before filtering/limiting so supporting evidence and distinct
source counts are not truncated. Use stable IDs to break equal timestamp ties.

The frontend defaults to all configured pairs. If none exist, it requests all
news. A user-selected subset with no remaining selected pairs pauses feed
requests and asks for a selection; it must not silently request all news.

### Feed envelope

| Field | Meaning |
| --- | --- |
| `items` | Article or event array. Empty is a valid successful result. |
| `total` | Total matching articles/events before the limit. Integer, at least `items.length`. |
| `lastSuccessfulRefreshAt` | Timestamp of the most recent successful backend collection, or `null` before any successful collection. Never replace this with HTTP response time. |
| `staleAfterSeconds` | Positive number defining when collection data becomes stale. The backend chooses it for its collection schedule. |

The latest 100 results are shown without pagination. The UI tells users when
additional results exist and suggests narrowing filters. A feed can be fresh
even when the newest article is old; freshness measures successful collection.
Partial collection successes may advance the feed timestamp, but failing sources
must remain degraded/unavailable in `/news/status` with their own timestamps.

Serve the last usable cache with HTTP 200 during provider failures, with honest
freshness and provider status. If there is no usable cache and collection is
unavailable, return an error such as 503 instead of pretending that no news
matches. A route that is not implemented returns 404 or 501; the frontend handles
that explicitly.

## Articles, events, and Claude insights

- Articles contain `id`, `sourceId`, `sourceName`, `url`, `headline`, `publishedAt`,
  optional publisher-provided `excerpt`, `category`, `matchedAssets`, and
  `matchedPairs`. Match fields are string arrays, including empty arrays when
  nothing matches. Do not put AI-generated text into a publisher excerpt.
- Events contain `id`, a source-grounded `headline`, `category`, `firstReportedAt`,
  `updatedAt`, both match arrays, `sourceCount`, `articles`, `insightStatus`, and
  `insight`. Every event has at least one supporting article. `sourceCount` is the
  number of distinct `sourceId` values, not article count. Articles and events
  must have unique IDs within their lists.
- `insightStatus` is `pending`, `validated`, or `unavailable`. For either
  non-display state (pending/unavailable), return `insight: null`.
- A validated insight contains its `eventId`, `generatedAt`, Claude `model`,
  `validationStatus: "validated"`, `confidence: "low" | "medium" | "high"`, and
  three nonempty statement arrays: `factualSummary`, `marketContext`, and
  `whatToWatch`.
- Every statement has nonempty `text` and a nonempty `articleIds` array. All IDs
  must resolve to supporting articles embedded in that event. The frontend links
  each statement to its cited originals and also exposes all supporting articles.

Backend validation must check structure, evidence references, factual grounding,
and informational-only output before setting `validated`. Do not produce buy/sell
instructions, entry/exit targets, or order recommendations. Confidence describes
evidence support, not likelihood of a price move. Validation is not a guarantee
of factual accuracy. When an event's evidence changes, revalidate or mark its
insight pending/unavailable instead of attaching an obsolete validated insight.

The frontend additionally checks insight structure and reference membership. It
discards unusable insights without hiding their events or original sources. It
does not perform semantic fact-checking or generate insights. Reported excerpts
are separated visually from the Claude section, whose factual summary is also
explicitly labeled AI-generated. Interpretation and what-to-watch content have
their own sub-section. News does not connect to order-entry actions.

## Source and AI status

`NewsStatus` contains:

- `checkedAt`: when these statuses were evaluated.
- `sources`: the full source catalog, including failed providers. Each entry has
  `id`, `name`, `status` (`healthy`, `degraded`, or `unavailable`), nullable
  `lastSuccessfulRefreshAt`, and optional `message`. Messages must be readable by
  traders and omit credentials, tracebacks, and internal infrastructure details.
- `categories`: the full category catalog as `{ id, label }` entries, independent
  of current feed results. Category IDs in reports must correspond to this list.
- `ai`: `{ status: "available" | "unavailable", message?: string }`. This describes
  the ability to produce new insights. Previously validated insights can remain
  visible while generation is unavailable.

All catalog IDs must be unique. Failure to fetch status means health is unknown;
it must not imply that every provider failed. The frontend keeps previously
loaded options/statuses with an explicit last-known warning if refresh fails.

## Frontend behavior and isolation

- Events and Articles use different React Query keys under `news`; every request
  filter and the limit are included. Only the selected mode fetches and polls.
- Feed and status refresh every 45 seconds while News is mounted and the browser
  tab is visible. Returning to the browser tab triggers a refresh. News queries
  unmount when changing top-level views; trading providers stay mounted.
- Filters and display mode are stored in App state across view changes. They
  reset on full browser reload; configured pairs retain their existing persistence.
- Manual Refresh reads the backend cache again; it does not force ingestion or
  Claude generation. A refresh failure retains same-filter cached results.
- Age and stale indicators update every 15 seconds and on visibility changes,
  using backend collection timestamps rather than React Query's cache age.
- There is no placeholder feed carried across different filters. Rendering/API
  errors stay within News and do not alter the header's trading status indicators.

## Verification and integration handoff

Use the existing frontend commands from `frontend/`:

```sh
npm run lint
npm run build
```

There is no added test runner, mock service worker, fixture set, automated
integration test suite, or backend stub. Browser checks use actual services.

Manual checks:

1. Start the terminal using [DEV_TESTING.md](../DEV_TESTING.md), open News, and
   confirm fourth-tab navigation. Before backend integration, expect the
   unavailable state; other views must remain usable.
2. With actual news routes connected, verify category/source/timeframe/pair
   requests in the browser Network panel. Check configured-pair defaults, no-pair
   fallback, subset selection, and filter persistence across view changes.
3. Open all original links, check event source counts and matches, and verify
   that factual summaries and interpretations have the appropriate Claude labels.
4. Observe 45-second feed/status requests, switch modes, hide the browser tab,
   leave News, and return. Only the active News mode should poll; trading
   WebSocket connections should remain intact.
5. Exercise loading, empty, stale, partial-provider-failure, AI-pending/unavailable,
   and refresh-failure states when the actual service supplies those conditions.
   Record conditions that could not be exercised; do not fabricate responses.
6. Check Dashboard, Trades, and Account normally. Any placement/cancellation
   checks use the documented OKX demo setup, not live trading.

Backend follow-up work must implement these contracts, ingestion/cache/grouping,
asset matching, and Claude generation/validation. Feedback remains deferred.

### Initial frontend verification (2026-09-22)

The production build and lint checks on all changed frontend files passed. The
full frontend lint command reports 9 existing errors and 3 warnings in unchanged
order-form, orderbook-hook, and WebSocket-context files.

Browser checks confirmed the unavailable-service state, the no-configured-pairs
fallback, navigation between all four views, and persistence of a changed
timeframe across navigation. These checks used an isolated browser without
configured trading accounts. Real feed content, original links, Claude insights,
provider failure/stale states, and live trading/WebSocket behavior still require
verification with the actual backend and documented demo trading setup.
