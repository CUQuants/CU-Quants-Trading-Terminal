# News Hub chart view validation

Run the frontend checks from `frontend/`:

```sh
npm run build
npm run test:news
npx eslint src/components/NewsView.tsx src/components/news src/types/news.ts
```

The 11 UI regression tests cover table columns and placeholders, excerpt/headline fallback, safe external links, 24-word previews, timestamp color boundaries and invalid dates, grouped-event source selection, and the Articles default/order. They bundle the actual production components with esbuild and render them with React's server renderer.

Run the isolated News backend contract tests from the repository root:

```sh
python -m pytest backend/tests/test_news_lifespan.py backend/tests/test_news_normalization.py backend/tests/test_news_providers.py backend/tests/test_news_routes.py backend/tests/test_news_service.py -q
```

## Results on 2026-10-10

- Production TypeScript/Vite build: passed.
- News UI regression tests: 11 passed.
- Focused News frontend lint: passed.
- News backend contract tests: 145 passed, one existing Starlette deprecation warning.
- Full backend suite: 185 passed, 12 failed. Nine failures are in the unimplemented Gemini service, two in Kraken (balance normalization and an order lifecycle test returning `EAPI:Invalid key`), and one in OKX order stream status emission. These source files were unchanged from the starting commit. The Kraken lifecycle test invokes the exchange API despite its `simulated=True` fixture; use the isolated News command above for this frontend work.
- Full frontend lint: nine errors and three warnings in unchanged trading components, exchange contexts, and orderbook hooks. No errors in the News files.

## Browser verification

- Fresh News mount defaults to Articles; Articles precedes Grouped events.
- All ten locally configured pairs appear as boxes, including pairs without news.
- XRP selection produces only XRP matches and a pressed blue box; clicking again clears pair filtering and restores all news.
- Category and last-hour filters produce the expected categories and relative timestamps.
- A pair with no reports and an unavailable source produce the empty-state message; Clear filters restores results.
- Provider status opens in the header and contains missing configuration details.
- At the annotated 2737 x 1290 desktop viewport, the heading and all filter controls share the header's vertical center, the table spans the window, and rows remain one line. The header padding is reduced from 28 to 20 pixels on each side vertically.
- Responsive follow-up: tested 320, 390, 768, 1280, 1800, and 2737-pixel window widths. Document, body, and News widths equal the viewport at every size, with no horizontal scroll containers. Below 1800px, filters open in a bounded panel instead of scrolling; pair boxes and app navigation wrap. The panel was also checked open at 320px. Time, asset, and headline stay visible on phones; category returns at 768px, pairs at 1024px, and price change at 1280px. Empty feeds keep chart headers visible.
- Live grouped events cannot be exercised against the currently running service, which returns News unavailable for that endpoint. Their rendering is covered by the UI regression tests.

The extra coin subscriptions were browser-local review configuration; this PR does not change default trading pairs.
