from unittest.mock import MagicMock, patch

from ai_news_radar.ingestion.rss import RssConnector

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>Company Launches New Model</title>
    <link>https://example.com/posts/new-model</link>
    <guid>https://example.com/posts/new-model</guid>
    <description>&lt;p&gt;A short &lt;b&gt;summary&lt;/b&gt; of the announcement.&lt;/p&gt;</description>
    <pubDate>Mon, 20 Oct 2025 10:00:00 GMT</pubDate>
  </item>
</channel>
</rss>
"""


@patch("ai_news_radar.ingestion.rss.requests.get")
def test_fetch_parses_and_strips_html(mock_get):
    mock_response = MagicMock()
    mock_response.text = SAMPLE_RSS
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    connector = RssConnector("example-blog", "https://example.com/feed.xml", source_type="company")
    items = connector.fetch()

    assert len(items) == 1
    item = items[0]
    assert item.external_id == "https://example.com/posts/new-model"
    assert item.title == "Company Launches New Model"
    assert item.url == "https://example.com/posts/new-model"
    assert "<p>" not in item.summary and "<b>" not in item.summary
    assert "summary" in item.summary
    assert item.published_at.year == 2025
