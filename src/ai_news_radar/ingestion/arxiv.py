from datetime import datetime

import feedparser
import requests

from ai_news_radar.ingestion.base import FetchedItem

ARXIV_API_URL = "http://export.arxiv.org/api/query"


class ArxivConnector:
    """Karar 1-A ornek connector: arXiv Atom API'sinden kategori bazli yeni makaleler."""

    source_name = "arxiv"
    source_type = "academic"

    def __init__(self, categories: list[str] | None = None, max_results: int = 25):
        self.categories = categories or ["cs.AI", "cs.LG", "cs.CL"]
        self.max_results = max_results

    def fetch(self) -> list[FetchedItem]:
        search_query = " OR ".join(f"cat:{c}" for c in self.categories)
        params = {
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": self.max_results,
        }
        response = requests.get(ARXIV_API_URL, params=params, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.text)

        items = []
        for entry in feed.entries:
            published_at = None
            if getattr(entry, "published_parsed", None):
                published_at = datetime(*entry.published_parsed[:6])
            items.append(
                FetchedItem(
                    external_id=entry.id,
                    title=entry.title.strip().replace("\n", " "),
                    url=entry.id,
                    summary=entry.summary.strip().replace("\n", " "),
                    published_at=published_at,
                )
            )
        return items
