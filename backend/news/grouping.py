import hashlib
import json
import re
from datetime import timedelta

from models import NewsArticle
from news.models import Article, NewsEvent

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "is",
    "of", "on", "the", "to", "with",
}


def source_id(source: str) -> str:
    base = source.split("/", 1)[0].strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "unknown"


def article_id(article: NewsArticle) -> str:
    published = article.published_at.isoformat() if article.published_at else ""
    value = article.url or f"{article.source}|{article.title}|{published}"
    return "article_" + hashlib.sha256(value.encode()).hexdigest()[:16]


def to_api_article(article: NewsArticle, pairs: list[str] | None = None) -> Article | None:
    if article.published_at is None:
        return None
    assets = sorted(set(article.assets))
    matched_pairs = []
    for pair in pairs or []:
        normalized = pair.upper()
        base = normalized.split("/", 1)[0]
        if "/" in normalized and base in assets and normalized not in matched_pairs:
            matched_pairs.append(normalized)
    return Article(
        id=article_id(article),
        source_id=source_id(article.source),
        source_name=article.source,
        url=article.url,
        headline=article.title,
        published_at=article.published_at,
        excerpt=article.summary or None,
        category=article.category,
        matched_assets=assets,
        matched_pairs=matched_pairs,
    )


def apply_pairs(event: NewsEvent, pairs: list[str]) -> NewsEvent:
    result = event.model_copy(deep=True)
    normalized_pairs = sorted({pair.upper() for pair in pairs if "/" in pair})
    for article in result.articles:
        article.matched_pairs = [
            pair
            for pair in normalized_pairs
            if pair.split("/", 1)[0] in article.matched_assets
        ]
    result.matched_pairs = sorted({
        pair for article in result.articles for pair in article.matched_pairs
    })
    return result


def _tokens(title: str) -> set[str]:
    return {
        word for word in _WORD_RE.findall(title.lower()) if word not in _STOP_WORDS
    }


def _same_story(article: Article, representative: Article) -> bool:
    if abs(article.published_at - representative.published_at) > timedelta(hours=12):
        return False
    left, right = _tokens(article.headline), _tokens(representative.headline)
    overlap = left & right
    if len(overlap) < 2:
        return False
    assets = set(article.matched_assets)
    representative_assets = set(representative.matched_assets)
    if assets and representative_assets and not assets & representative_assets:
        return False
    score = len(overlap) / len(left | right)
    return score >= (0.55 if assets and representative_assets else 0.72)


def _content_hash(articles: list[Article]) -> str:
    content = [
        {
            "id": article.id,
            "headline": article.headline,
            "excerpt": article.excerpt,
            "publishedAt": article.published_at.isoformat(),
            "assets": article.matched_assets,
        }
        for article in sorted(articles, key=lambda item: item.id)
    ]
    value = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def _make_event(articles: list[Article]) -> NewsEvent:
    ordered = sorted(articles, key=lambda item: item.published_at, reverse=True)
    first = ordered[-1]
    return NewsEvent(
        id="event_" + hashlib.sha256(first.id.encode()).hexdigest()[:16],
        headline=ordered[0].headline,
        category=ordered[0].category,
        first_reported_at=first.published_at,
        updated_at=ordered[0].published_at,
        matched_assets=sorted({
            asset for article in ordered for asset in article.matched_assets
        }),
        matched_pairs=[],
        source_count=len({article.source_id for article in ordered}),
        articles=ordered,
        content_hash=_content_hash(ordered),
    )


def group_articles(articles: list[NewsArticle]) -> list[NewsEvent]:
    """Group likely reports of the same event after exact URL deduplication."""
    api_articles = []
    seen_ids: set[str] = set()
    for article in articles:
        item = to_api_article(article)
        if item and item.id not in seen_ids:
            api_articles.append(item)
            seen_ids.add(item.id)
    groups: list[list[Article]] = []
    for article in sorted(api_articles, key=lambda item: item.published_at):
        for group in groups:
            if _same_story(article, group[0]):
                group.append(article)
                break
        else:
            groups.append([article])
    events = [_make_event(group) for group in groups]
    return sorted(events, key=lambda event: event.updated_at, reverse=True)
