from unittest.mock import MagicMock, patch

from ai_news_radar.ingestion.hackernews import HackerNewsConnector

SAMPLE_RESPONSE = {
    "hits": [
        {
            "objectID": "111",
            "title": "New open-weight model beats benchmark",
            "url": "https://example.com/new-model",
            "points": 120,
            "num_comments": 45,
            "created_at": "2025-10-20T08:30:00.000Z",
        },
        {
            "objectID": "222",
            "title": "Ask HN: How are you using local LLMs?",
            "url": None,
            "story_text": "<p>Curious about everyone's <b>local</b> setup.</p>",
            "points": 60,
            "num_comments": 30,
            "created_at": "2025-10-21T09:00:00.000Z",
        },
    ]
}


@patch("ai_news_radar.ingestion.hackernews.requests.get")
def test_fetch_parses_hits(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = HackerNewsConnector(query="AI", min_points=30, max_results=10)
    items = connector.fetch()

    assert len(items) == 2

    linked = items[0]
    assert linked.external_id == "111"
    assert linked.url == "https://example.com/new-model"
    assert "120 puan" in linked.summary
    assert linked.published_at.year == 2025

    self_post = items[1]
    assert self_post.external_id == "222"
    assert self_post.url == "https://news.ycombinator.com/item?id=222"
    assert "<p>" not in self_post.summary and "<b>" not in self_post.summary
    assert "local" in self_post.summary
