from unittest.mock import MagicMock, patch

from ai_news_radar.ingestion.huggingface_papers import HuggingFaceDailyPapersConnector

SAMPLE_RESPONSE = [
    {
        "paper": {"id": "2610.31372", "summary": "This paper proposes a new method for X."},
        "title": "RIDAR: Safeguarding Research Integrity",
        "publishedAt": "2026-10-21T20:00:00.000Z",
    },
    {
        "paper": {"id": "2610.12586", "summary": "A second paper about Y."},
        "title": "Realism vs Accuracy",
        "publishedAt": "2026-10-07T20:00:00.000Z",
    },
]


@patch("ai_news_radar.ingestion.huggingface_papers.requests.get")
def test_fetch_parses_daily_papers(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = HuggingFaceDailyPapersConnector(max_results=2)
    items = connector.fetch()

    assert len(items) == 2
    item = items[0]
    assert item.external_id == "2610.31372"
    assert item.title == "RIDAR: Safeguarding Research Integrity"
    assert item.url == "https://huggingface.co/papers/2610.31372"
    assert "new method" in item.summary
    assert item.published_at.year == 2026
