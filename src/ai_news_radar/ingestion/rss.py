from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

from ai_news_radar.ingestion.base import FetchedItem, strip_html

USER_AGENT = "Mozilla/5.0 (compatible; ai-news-radar/0.1)"


def select_recent(items, max_results, lookback_days=None, latest_fallback=0, *, now=None):
    """Prefer recent publications; never relabel old or undated items as new."""
    items = sorted(items, key=lambda item: item.published_at or datetime.min, reverse=True)
    if lookback_days is not None:
        now = now or datetime.now(UTC).replace(tzinfo=None)
        dated = [item for item in items if item.published_at and item.published_at <= now]
        cutoff = now - timedelta(days=lookback_days)
        recent = [item for item in dated if item.published_at >= cutoff]
        items = recent or dated[:latest_fallback]
    return items[:max_results]


class RssConnector:
    """Karar 1-A: RSS/Atom besleyen sirket/medya kaynaklari icin genel connector."""

    def __init__(
        self, source_name: str, feed_url: str, source_type: str = "company", max_results: int = 15,
        *, lookback_days: int | None = None, latest_fallback: int = 0
    ):
        self.source_name = source_name
        self.source_type = source_type
        self.feed_url = feed_url
        self.max_results = max_results
        self.lookback_days = lookback_days
        self.latest_fallback = latest_fallback

    def fetch(self) -> list[FetchedItem]:
        response = requests.get(self.feed_url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        if not feed.version:
            raise ValueError('Source did not return an RSS/Atom feed')

        items = []
        for entry in feed.entries:
            if not entry.get('title') or urlsplit(entry.get('link', '')).scheme not in ('http', 'https'):
                continue
            published_at = None
            source_date = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if source_date:
                published_at = datetime(*source_date[:6])

            external_id = getattr(entry, "id", None) or entry.link
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            items.append(
                FetchedItem(
                    external_id=external_id,
                    title=strip_html(entry.title).strip().replace("\n", " "),
                    url=entry.link,
                    summary=strip_html(summary).strip().replace("\n", " "),
                    published_at=published_at,
                )
            )
        if items and self.lookback_days is not None and not any(item.published_at for item in items):
            raise ValueError('RSS/Atom feed has no usable publication dates')
        return select_recent(items, self.max_results, self.lookback_days, self.latest_fallback)


class MultiRssConnector(RssConnector):
    """Merge overlapping topic feeds under one source and stable article URL."""

    def __init__(self, source_name, feed_urls, **kwargs):
        super().__init__(source_name, feed_urls[0], **kwargs)
        self.feed_urls = feed_urls

    def fetch(self):
        unique = {}
        for url in self.feed_urls:
            connector = RssConnector(self.source_name, url, self.source_type, self.max_results,
                                     lookback_days=self.lookback_days, latest_fallback=self.latest_fallback)
            for item in connector.fetch():
                parts = urlsplit(item.url)
                canonical = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
                item.external_id = canonical
                item.url = canonical
                unique.setdefault(canonical, item)
        return select_recent(list(unique.values()), self.max_results, self.lookback_days, self.latest_fallback)
