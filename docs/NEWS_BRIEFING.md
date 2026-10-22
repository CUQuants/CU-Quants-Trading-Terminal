# News backend implementation briefing

Date: 2026-09-21

## Delivered scope

| Requested task | Implementation |
| --- | --- |
| 1. Port XLRTS providers | `backend/news/providers.py`: Finnhub, CryptoPanic, CoinDesk, Messari, Alpaca, Marketaux, NewsAPI, and optional yFinance. Async HTTP, current Messari fields, explicit credentials, partial results, safe errors. |
| 2. Normalize articles | `backend/news/normalization.py`: plain text, validated titles, UTC dates or null for unknown dates, consistent Pydantic article shape. |
| 3. Categorize and match assets/pairs | XLRTS category precedence, symbol/name matching, canonical `BASE/QUOTE` labels, `XBT`/`BTC` aliases, and per-request matching on copies. |
| 4. Remove exact duplicate URLs | First received nonempty exact URL wins. URL variants and blank URLs remain separate. |
| 5. Five-minute refresh | Lifespan-managed startup refresh and a 300-second schedule; concurrent sources, overlap prevention, timeouts, and cancellation. |
| 6. In-memory cache | Atomic snapshots, newest-first output, 500-article visible limit, bounded provider snapshots, and one-hour expiry. Failed providers retain usable cached data. |
| 7. Provider health/failures | Disabled/pending/ok/degraded/error states, attempt/success times, safe failure codes, total/consecutive failures, counts, and freshness. |
| 8. `/news` and `/news/status` | Typed FastAPI routes. News supports category/source/search filters, pagination, requested pairs/assets, and matched-only output. Reads never trigger upstream calls. |
| 9. Tests | Offline provider, normalization, service, route, and app-lifespan coverage. |

The implementation follows the terminal's existing router, shared Pydantic
model, async HTTP, application-state, lifespan, and pytest/TestClient patterns.
The XLRTS desktop UI and trading logic are not dependencies of the news service.

## Verification

- **116 tests passed**: 34 provider, 52 normalization, 17 service, 11 route, and
  2 isolated app-lifespan cases. The only warning was a Starlette/httpx
  TestClient deprecation; no news test failures occurred.
- The actual 300-second scheduler ran two callbacks **300.006 seconds apart**
  using a deterministic provider. The second callback replaced the cached
  article, and shutdown stopped the task cleanly. This was a real-time check,
  separate from the short-interval unit tests.
- The final live, unauthenticated Yahoo refresh returned **66 normalized
  articles** in approximately **2.2 seconds**. `/news` and `/news/status` both returned **200**.
  No saved credentials were loaded, and no exchange endpoints were contacted.
- All seven credentialed providers reported `disabled` with their missing
  configuration names during that probe. Their account access remains untested.
- Syntax compilation, whitespace validation, and the dependency lockfile check
  passed. Testing used Python 3.14.3, which satisfies the backend's `>=3.12`
  requirement.
- Verification processes exited cleanly. The ongoing refresh task starts with
  the terminal app once its existing SDK prerequisite is satisfied.

## Existing deployment blocker

The full backend suite stops during collection because the sibling
`proxy-client` 0.3.0 checkout does not export `ReportingClient`. The terminal's
existing `exchange_services/reporting_session.py` imports that class; clean
`HEAD` reproduces the same import error. Normal app startup is also affected.

Before running the whole terminal, synchronize or pin a compatible SDK revision
that provides the reporting client. The news lifespan tests isolate trading
collaborators to verify the new wiring; they do not conceal this dependency
problem or prove full trading-app integration. No reporting or SDK implementation
was changed.

## Operational boundaries

- Set provider credentials in `backend/.env`; install Yahoo with
  `uv sync --extra news`. Missing configuration affects only that provider.
- Provider account access, plan limits, and CryptoPanic's configured v2 plan
  require deployment validation. Polling is five-minute by design, which may
  exceed some free-tier quotas.
- The cache is process-local and disappears on restart. Multiple workers create
  independent refresh loops and caches.
- A degraded batch preserves earlier articles without renewing their expiry;
  new articles added to that partial snapshot inherit its earlier expiry.
- Category and asset matching use documented heuristics. URL deduplication does
  not identify syndicated stories or similar headlines at different URLs.

See [backend/README.md](../backend/README.md) for the complete API contract,
environment variables, provider references, and test commands.
