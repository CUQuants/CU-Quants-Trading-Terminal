import hashlib
import json
import re
from datetime import timedelta

from .models import Article, NewsEvent

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def _title_tokens(title: str) -> set[str]:
    return {
        word for word in _WORD_RE.findall(title.lower()) if word not in _STOP_WORDS
    }


def _similarity(left: str, right: str) -> tuple[float, int]:
    left_tokens = _title_tokens(left)
    right_tokens = _title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0, 0
    overlap = left_tokens & right_tokens
    return len(overlap) / len(left_tokens | right_tokens), len(overlap)


def _same_story(article: Article, representative: Article) -> bool:
    time_gap = abs(article.published_at_utc - representative.published_at_utc)
    if time_gap > timedelta(hours=12):
        return False

    score, overlap = _similarity(article.title, representative.title)
    if overlap < 2:
        return False

    article_assets = {asset.upper() for asset in article.assets}
    representative_assets = {asset.upper() for asset in representative.assets}
    if article_assets and representative_assets and not article_assets & representative_assets:
        return False

    threshold = 0.55 if article_assets and representative_assets else 0.72
    return score >= threshold


def _content_hash(articles: list[Article]) -> str:
    content = [
        {
            "id": article.id,
            "title": article.title,
            "excerpt": article.excerpt,
            "published_at": article.published_at_utc.isoformat(),
            "assets": sorted(article.assets),
            "pairs": sorted(article.matched_pairs),
        }
        for article in sorted(articles, key=lambda item: item.id)
    ]
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _make_event(articles: list[Article]) -> NewsEvent:
    ordered = sorted(
        articles,
        key=lambda item: (item.published_at_utc, item.id),
        reverse=True,
    )
    representative = ordered[0]
    first = min(ordered, key=lambda item: (item.published_at_utc, item.id))
    event_id = "evt_" + hashlib.sha256(first.id.encode()).hexdigest()[:16]

    return NewsEvent(
        id=event_id,
        representative_article_id=representative.id,
        related_article_ids=[article.id for article in ordered],
        headline=representative.title,
        category=representative.category,
        assets=sorted(
            {asset.upper() for article in ordered for asset in article.assets}
        ),
        matched_pairs=sorted(
            {pair.upper() for article in ordered for pair in article.matched_pairs}
        ),
        first_published_at_utc=min(article.published_at_utc for article in ordered),
        last_updated_at_utc=max(article.ingested_at_utc for article in ordered),
        articles=ordered,
        content_hash=_content_hash(ordered),
    )


def group_articles(articles: list[Article]) -> list[NewsEvent]:
    """Remove exact URLs, then conservatively group reports of one event."""
    unique: list[Article] = []
    seen_urls: set[str] = set()

    for article in sorted(
        articles,
        key=lambda item: (item.published_at_utc, item.id),
        reverse=True,
    ):
        url = article.canonical_url.rstrip("/")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append(article)

    groups: list[list[Article]] = []
    for article in reversed(unique):
        for group in groups:
            if _same_story(article, group[0]):
                group.append(article)
                break
        else:
            groups.append([article])

    events = [_make_event(group) for group in groups]
    return sorted(events, key=lambda event: event.first_published_at_utc, reverse=True)
