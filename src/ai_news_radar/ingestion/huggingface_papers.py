from datetime import datetime

import requests

from ai_news_radar.ingestion.base import FetchedItem

DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


class HuggingFaceDailyPapersConnector:
    """Karar 1-A: Hugging Face'in kendi kuratorlugunu yaptigi gunluk one cikan
    model/arastirma makaleleri - her girdi neyin ne ise yaradigini anlatan
    gercek bir ozet (abstract) iceriyor, ham Hub API'si (createdAt sirali)
    aksine gurultusuz."""

    source_type = "academic"

    def __init__(self, source_name: str = "huggingface-daily-papers", max_results: int = 10):
        self.source_name = source_name
        self.max_results = max_results

    def fetch(self) -> list[FetchedItem]:
        response = requests.get(DAILY_PAPERS_URL, timeout=30)
        response.raise_for_status()
        entries = response.json()[: self.max_results]

        items = []
        for entry in entries:
            paper = entry["paper"]
            published_at = None
            published_raw = entry.get("publishedAt")
            if published_raw:
                published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))

            items.append(
                FetchedItem(
                    external_id=paper["id"],
                    title=entry["title"].strip(),
                    url=f"https://huggingface.co/papers/{paper['id']}",
                    summary=paper.get("summary", "").strip(),
                    published_at=published_at,
                )
            )
        return items
