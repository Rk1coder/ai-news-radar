from datetime import datetime

import requests

from ai_news_radar.ingestion.base import FetchedItem, strip_html

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsConnector:
    """Karar 1-A: Hacker News (Algolia API) uzerinden sosyal/topluluk kaynagi denemesi."""

    source_type = "social"

    def __init__(
        self,
        source_name: str = "hackernews-ai",
        query: str = "AI",
        min_points: int = 30,
        max_results: int = 10,
    ):
        self.source_name = source_name
        self.query = query
        self.min_points = min_points
        self.max_results = max_results

    def fetch(self) -> list[FetchedItem]:
        params = {
            "tags": "story",
            "query": self.query,
            "numericFilters": f"points>{self.min_points}",
            "hitsPerPage": self.max_results,
        }
        response = requests.get(HN_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        hits = response.json().get("hits", [])

        items = []
        for hit in hits:
            object_id = hit["objectID"]
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
            story_text = hit.get("story_text")
            summary = (
                strip_html(story_text).strip()
                if story_text
                else f"Hacker News'te {hit.get('points', 0)} puan, "
                f"{hit.get('num_comments', 0)} yorum."
            )
            published_at = None
            created_at = hit.get("created_at")
            if created_at:
                published_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            items.append(
                FetchedItem(
                    external_id=str(object_id),
                    title=hit["title"],
                    url=url,
                    summary=summary,
                    published_at=published_at,
                )
            )
        return items
