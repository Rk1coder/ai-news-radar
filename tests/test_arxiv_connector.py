from unittest.mock import MagicMock, patch

from ai_news_radar.ingestion.arxiv import ArxivConnector

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <title>  A Novel Approach to Something
</title>
    <summary>  This paper proposes a new method.
</summary>
    <published>2025-01-01T12:00:00Z</published>
  </entry>
</feed>
"""


@patch("ai_news_radar.ingestion.arxiv.requests.get")
def test_fetch_parses_entries(mock_get):
    mock_response = MagicMock()
    mock_response.text = SAMPLE_FEED
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = ArxivConnector(categories=["cs.AI"], max_results=5)
    items = connector.fetch()

    assert len(items) == 1
    item = items[0]
    assert item.external_id == "http://arxiv.org/abs/2501.00001v1"
    assert item.title == "A Novel Approach to Something"
    assert "new method" in item.summary
    assert item.published_at.year == 2025
