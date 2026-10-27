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


@patch("ai_news_radar.ingestion.rss.requests.get")
def test_atom_updated_date_is_used_when_published_is_missing(mock_get):
    from datetime import datetime
    mock_get.return_value.text = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <id>release-1</id><title>Release</title><link href="https://example.com/release"/>
      <updated>2026-10-24T23:15:00Z</updated><summary>Changes</summary>
    </entry></feed>'''
    items = RssConnector("releases", "https://example.com/feed").fetch()
    assert items[0].published_at == datetime(2026, 10, 24, 23, 15)


def test_recent_window_sorts_before_limiting_and_excludes_future_and_undated():
    from datetime import datetime, timedelta
    from ai_news_radar.ingestion.base import FetchedItem
    from ai_news_radar.ingestion.rss import select_recent
    now = datetime(2026, 10, 26, 12)
    def item(name, days):
        return FetchedItem(name, name, 'https://example.com/' + name, '',
                           now - timedelta(days=days) if days is not None else None)
    items = [item('old', 9), item('recent', 3), item('future', -1),
             item('unknown', None), item('newest', 0), item('boundary', 4)]
    selected = select_recent(items, 2, 4, now=now)
    assert [i.title for i in selected] == ['newest', 'recent']
    assert len(select_recent(items, 10, 4, now=now)) == 3
    assert select_recent([item('old', 9), item('older', 20)], 5, 4, 1, now=now)[0].title == 'old'
    assert select_recent([item('unknown', None), item('future', -1)], 5, 4, 1, now=now) == []


@patch('ai_news_radar.ingestion.rss.requests.get')
def test_html_error_page_is_not_a_successful_empty_feed(mock_get):
    import pytest
    mock_get.return_value.text = '<html><title>Access denied</title></html>'
    with pytest.raises(ValueError, match='RSS|Atom'):
        RssConnector('blocked', 'https://example.com/feed').fetch()


@patch('ai_news_radar.ingestion.rss.requests.get')
def test_multiple_medium_tags_deduplicate_urls_without_tracking(mock_get):
    first, second = MagicMock(), MagicMock()
    first.text = SAMPLE_RSS.replace('/posts/new-model</link>', '/posts/new-model?source=ai</link>')
    second.text = SAMPLE_RSS.replace('/posts/new-model</link>', '/posts/new-model?source=automation</link>')
    mock_get.side_effect = [first, second]
    from ai_news_radar.ingestion.rss import MultiRssConnector
    connector = MultiRssConnector('medium', ['https://example.com/ai', 'https://example.com/automation'])
    assert len(connector.fetch()) == 1
