import assert from 'node:assert/strict';
import test from 'node:test';
import { build } from 'esbuild';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

// Bundle the production components using Vite's existing compiler dependency.
const result = await build({
  stdin: {
    contents: `export { NewsTable } from './src/components/news/NewsTable';
      export { NewsFilters } from './src/components/news/NewsFilters';
      export { DEFAULT_NEWS_VIEW_STATE } from './src/types/news';
      export { createElement } from 'react';
      export { renderToStaticMarkup } from 'react-dom/server';`,
    resolveDir: process.cwd(),
  },
  bundle: true,
  write: false,
  platform: 'node',
  jsx: 'automatic',
  format: 'esm',
  packages: 'external',
  define: { 'process.env.NODE_ENV': '"production"' },
});
const tempDir = await mkdtemp(join(process.cwd(), 'tests', '.news-test-'));
let ui;
try {
  const bundlePath = join(tempDir, 'components.mjs');
  await writeFile(bundlePath, result.outputFiles[0].text);
  ui = await import(pathToFileURL(bundlePath).href);
} finally {
  await rm(tempDir, { recursive: true, force: true });
}
const now = Date.parse('2026-10-10T12:00:00Z');
const article = {
  id: 'a1', headline: 'Headline fallback', excerpt: 'Extracted report excerpt',
  url: 'https://example.com/report', publishedAt: new Date(now).toISOString(),
  matchedAssets: ['BTC'], matchedPairs: ['BTC/USD'], category: 'crypto',
};
function table(item = article) {
  return ui.renderToStaticMarkup(ui.createElement(ui.NewsTable, {
    items: [item], now, categoryLabel: () => 'Crypto',
  }));
}

test('table exposes all six accessible columns and price placeholder', () => {
  const html = table();
  assert.equal((html.match(/scope="col"/g) ?? []).length, 6);
  for (const label of ['Posted', 'Asset name', 'Pairs', 'Price change', 'Category', 'Excerpt / headline']) assert.ok(html.includes(label));
  assert.ok(html.includes('Asset price change not connected'));
});
test('excerpt supplies link text with full text available as a tooltip', () => {
  const html = table();
  assert.ok(html.includes('title="Extracted report excerpt"'));
  assert.ok(html.includes('Extracted report excerpt<span'));
  assert.ok(html.includes('target="_blank" rel="noopener noreferrer"'));
});
test('missing or whitespace excerpt falls back to headline', () => {
  for (const excerpt of [null, '', '   ']) assert.ok(table({ ...article, excerpt }).includes('Headline fallback<span'));
});
test('long excerpts stop at 24 words, retain full tooltip and cannot wrap', () => {
  const words = Array.from({ length: 30 }, (_, i) => `word${i + 1}`);
  const html = table({ ...article, excerpt: words.join(' ') });
  assert.ok(html.includes(`${words.slice(0, 24).join(' ')}…<span`));
  assert.ok(html.includes(`title="${words.join(' ')}"`));
  assert.ok(html.includes('leading-snug truncate'));
});
test('unsafe and malformed URLs remain text rather than active links', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,unsafe', 'file:///secret', 'invalid']) {
    const html = table({ ...article, url });
    assert.ok(!html.includes('<a '));
    assert.ok(html.includes('(link unavailable)'));
  }
});
test('unmatched assets and pairs have meaningful placeholders', () => {
  const html = table({ ...article, matchedAssets: [], matchedPairs: [] });
  assert.ok(html.includes('General market'));
  assert.ok(html.includes('>—</td>'));
});
test('posted time fades from Quants blue to gray and clamps future dates', () => {
  for (const [age, color] of [[-60000, '47, 113, 200'], [0, '47, 113, 200'], [1800000, '98, 131, 174'], [3600000, '148, 148, 148'], [7200000, '148, 148, 148']]) {
    assert.ok(table({ ...article, publishedAt: new Date(now - age).toISOString() }).includes(`color:rgb(${color})`));
  }
});
test('invalid timestamps render safely', () => {
  const html = table({ ...article, publishedAt: 'invalid' });
  assert.ok(html.includes('Unknown time'));
  assert.ok(html.includes('color:rgb(148, 148, 148)'));
});
test('grouped events link to the article supplying the excerpt', () => {
  const html = table({ ...article, firstReportedAt: article.publishedAt, articles: [
    { ...article, excerpt: null },
    { ...article, id: 'a2', excerpt: 'Second source excerpt', url: 'https://example.com/second' },
  ] });
  assert.ok(html.includes('href="https://example.com/second"'));
  assert.ok(html.includes('Second source excerpt<span'));
});
test('events without source articles safely render their headline', () => {
  const html = table({ ...article, firstReportedAt: article.publishedAt, articles: [] });
  assert.ok(html.includes('<span>Headline fallback</span>'));
  assert.ok(!html.includes('<a '));
});
test('Articles is first and is the default selected mode', () => {
  assert.equal(ui.DEFAULT_NEWS_VIEW_STATE.mode, 'articles');
  const html = ui.renderToStaticMarkup(ui.createElement(ui.NewsFilters, {
    state: ui.DEFAULT_NEWS_VIEW_STATE, configuredPairs: [], onChange() {},
  }));
  assert.ok(html.indexOf('>Articles</button>') < html.indexOf('>Grouped events</button>'));
  assert.match(html, /aria-pressed="true"[^>]*>Articles<\/button>/);
});
