# Terminal backend

FastAPI routes use Pydantic response models from `models.py`, with services owned
by the application lifespan. Run from this directory:

```bash
uv sync --extra news
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The `news` extra installs the optional Yahoo Finance adapter. The other seven
adapters use the existing `httpx` dependency. Copy `.env.example` to `.env` and
configure the terminal's existing proxy credentials as described in
[DEV_TESTING.md](../DEV_TESTING.md). News credentials are optional and independent
of exchange credentials. Never copy credentials into source files.

The sibling `proxy-client` must export `ReportingClient` for the existing app
imports to work. The local SDK checkout inspected during this implementation
does not; see the [implementation briefing](../docs/NEWS_BRIEFING.md) for the
verification boundary and deployment prerequisite.

## News API

`GET /news` returns a JSON array of cached articles, newest first. It does not
contact upstream providers. An empty cache, including initial startup, returns
`[]`; consult `/news/status` to distinguish pending, disabled, and failed sources.

```bash
curl "http://localhost:8000/news?pairs=BTC%2FUSD&pairs=ETH%2FUSD&limit=20"
curl "http://localhost:8000/news?assets=SOL&matched_only=true&category=Crypto"
curl "http://localhost:8000/news/status"
```

| Parameter | Behavior |
| --- | --- |
| `pairs` | Repeat for each pair. Accepts `BTC/USD`, `BTC-USD`, or `BTC_USD`; labels use `BASE/QUOTE`, with `XBT` mapped to `BTC`. |
| `assets` | Repeat for symbols or recognized asset names, such as `BTC` or `Bitcoin`. |
| `matched_only` | Defaults to `false`. When true, retain articles matching the requested pairs or assets. |
| `category` | `All`, `Crypto`, `Trad-Fi`, `FX/Macro`, or `Geo-Politics`. |
| `source` | Case-insensitive exact source or provider name, such as `Finnhub` or `Finnhub/Reuters`. |
| `q` | Case-insensitive title/summary substring search. |
| `limit`, `offset` | Pagination after filtering; limit defaults to 100, maximum 500; offset defaults to 0. |

```json
[
  {
    "source": "Example",
    "title": "Bitcoin market update",
    "summary": "A normalized plain-text summary.",
    "url": "https://example.test/story",
    "published_at": "2026-09-21T12:00:00Z",
    "category": "Crypto",
    "assets": ["BTC"],
    "matched": true,
    "match_terms": ["BTC/USD"]
  }
]
```

Normalization strips markup, decodes entities, rejects missing titles, and
converts supported timestamps to UTC. Unknown or invalid publication times stay
`null` and sort last. Category precedence follows XLRTS: geopolitical terms,
explicit provider category, provider defaults, keyword fallback, then Trad-Fi.
Matching uses asset names and bounded symbol matches; a quote currency alone
does not match every pair. Matching is a relevance hint, not entity recognition.
Each request receives copies so its pair list cannot alter another user's cache.

Deduplication compares exact nonempty URLs after surrounding whitespace is
trimmed. The first completed provider supplying a URL wins. Tracking parameters,
URL case, and different URLs for the same story remain distinct; blank URLs are
retained. There is no persistent cross-refresh duplicate history.

## Refresh, cache, and health

`NewsService` starts immediately in the FastAPI lifespan and schedules another
refresh every 300 seconds. It fetches enabled providers concurrently, prevents
overlapping refreshes, and cancels the task and closes its HTTP pool on shutdown.
Upstream HTTP requests have an eight-second timeout; each provider has a
30-second overall budget. Yahoo's blocking library runs outside the event loop
with a 20-second batch deadline, returning partial results if that deadline is
reached.

Readers keep the previous complete cache while a refresh is running. Completed
refreshes replace the snapshot atomically. Successful empty feeds clear that
provider's previous articles. A failure keeps its previous snapshot for up to one
hour from retrieval; partial failures combine new and previous articles without
extending the old snapshot's lifetime. This conservative rule may also expire
new additions to a degraded snapshot at that earlier deadline. Cache reads
enforce expiry even if no refresh completes. The visible cache contains at most
500 articles, and each provider snapshot is also capped at 500.

`GET /news/status` reports:

- `refresh_interval_seconds`, `refreshing`, `last_refresh`, `last_success`, and
  `next_refresh` for the scheduler.
- `article_count` after deduplication and the cache limit, plus `stale` when no
  enabled provider has a fresh, successful snapshot.
- `providers`, each containing `name`, `enabled`, `state`, `disabled_reason`,
  `last_attempt`, `last_success`, `last_error`, `consecutive_failures`,
  `total_failures`, `article_count`, and `stale`.

Provider states are `disabled`, `pending`, `ok`, `degraded` (usable articles plus
failures), and `error`. A successful response resets consecutive failures but
preserves the total. `last_success` includes usable partial responses and valid
empty feeds. A provider is stale on failure, before any response, after expiry,
or when its cached response is at least two refresh intervals old. Overall
freshness can remain healthy while one provider fails; inspect provider states
for coverage. Failure messages contain safe error codes, never raw upstream
responses, exception messages, or credential-bearing URLs.

This cache is process-local, disappears on restart, and is independent in each
worker. Use one backend worker if you need one refresh schedule and shared news
view across requests. A continuously enabled provider is polled up to 288 times
per day (Finnhub makes two requests per refresh, Yahoo up to eight ticker calls).
Enable only providers whose plan permits that cadence; quota errors are visible
in status and do not erase other sources.

## Providers and configuration

Configuration is read when the service is created. Restart after changing keys.
Disabled providers remain visible in status and make no requests.

| Provider | Environment variables | Notes |
| --- | --- | --- |
| Finnhub | `FINNHUB_KEY` | General and crypto feeds; preserves partial success if one fails. |
| CryptoPanic | `CRYPTOPANIC_KEY`, `CRYPTOPANIC_PLAN` | v2 posts, with the configured subscription path; plan defaults to `growth`. |
| CoinDesk | `COINDESK_KEY` | Uses authenticated news API access. |
| Messari | `MESSARI_KEY` | Current news feed API with asset symbols. |
| Alpaca | `ALPACA_KEY`, `ALPACA_SECRET` | Market news including provider symbols. |
| Marketaux | `MARKETAUX_KEY` | English-language feed with entity symbols; FX/Macro source default follows XLRTS. |
| NewsAPI | `NEWSAPI_KEY` | US business headlines. |
| yFinance | Optional `NEWS_YFINANCE_ENABLED` | Enabled when the `news` extra is installed; set `false` to disable. No API key. Supports both legacy and nested Yahoo article schemas. |

These adapters port XLRTS provider intent into the terminal's async service
architecture. The old CryptoPanic and Messari no-key assumptions are not carried
forward. Credentials, provider plans, and upstream availability determine which
feeds actually work; a passing offline adapter test does not verify an account.
CryptoPanic's plan-specific v2 adapter is covered by fixtures, but its current
subscription access and response must still be verified with a deployment key.

Provider references: [Finnhub market news](https://finnhub.io/docs/api/market-news),
[CryptoPanic API](https://cryptopanic.com/developers/api/),
[CoinDesk news API](https://developers.coindesk.com/documentation/data-api/news_v1_article_list),
[Messari news feed](https://docs.messari.io/api-reference/endpoints/news/get-v1-news-feed),
[Alpaca news](https://docs.alpaca.markets/us/reference/news-3),
[Marketaux API](https://www.marketaux.com/documentation),
[NewsAPI headlines](https://newsapi.org/docs/endpoints/top-headlines), and
[yfinance source](https://github.com/ranaroussi/yfinance).

## Tests

```bash
uv run pytest tests/test_news_providers.py tests/test_news_normalization.py tests/test_news_service.py tests/test_news_routes.py tests/test_news_lifespan.py -q
uv run pytest tests -q
```

The news tests use `httpx.MockTransport`, fake providers, and FastAPI's existing
`TestClient` pattern. They do not require credentials or live network access.
The lifespan tests load the real app wiring with fake trading collaborators;
they verify news startup and cleanup without claiming external SDK integration.
The full backend suite additionally requires a sibling `proxy-client` checkout
that exports `ReportingClient`, as expected by the existing reporting service.
