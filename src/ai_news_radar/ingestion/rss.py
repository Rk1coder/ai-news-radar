import re
from datetime import datetime

import feedparser
import requests

from ai_news_radar.ingestion.base import FetchedItem

USER_AGENT = "Mozilla/5.0 (compatible; ai-news-radar/0.1)"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text)


class RssConnector:
    """Karar 1-A: RSS/Atom besleyen sirket/medya kaynaklari icin genel connector."""

    def __init__(
        self, source_name: str, feed_url: str, source_type: str = "company", max_results: int = 15
    ):
        self.source_name = source_name
        self.source_type = source_type
        self.feed_url = feed_url
        self.max_results = max_results

    def fetch(self) -> list[FetchedItem]:
        response = requests.get(self.feed_url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.text)

        items = []
        for entry in feed.entries[: self.max_results]:
            published_at = None
            if getattr(entry, "published_parsed", None):
                published_at = datetime(*entry.published_parsed[:6])

            external_id = getattr(entry, "id", None) or entry.link
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            items.append(
                FetchedItem(
                    external_id=external_id,
                    title=_strip_html(entry.title).strip().replace("\n", " "),
                    url=entry.link,
                    summary=_strip_html(summary).strip().replace("\n", " "),
                    published_at=published_at,
                )
            )
        return items
