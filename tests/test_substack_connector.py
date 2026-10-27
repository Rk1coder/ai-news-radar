import json
from datetime import datetime
from unittest.mock import patch

import pytest

from ai_news_radar.ingestion.substack import SubstackTopicsConnector


def page(posts):
    return '<script type="application/json" id="preloads-json">' + json.dumps({'posts': posts, 'comments': [{'title': 'not a post'}]}) + '</script>'


@patch('ai_news_radar.ingestion.substack.requests.get')
def test_topic_reads_latest_public_posts_with_real_dates_and_no_duplicates(get):
    older = {'id': 1, 'title': 'Older &amp; useful', 'canonical_url': 'https://example.substack.com/p/old', 'post_date': '2026-10-09T18:00:00Z', 'subtitle': '<b>Public summary</b>'}
    newer = {**older, 'id': 2, 'title': 'Latest', 'canonical_url': 'https://example.substack.com/p/latest', 'post_date': '2026-10-25T12:30:00+02:00'}
    get.return_value.text = page([older, newer, newer, {**older, 'canonical_url': 'javascript:alert(1)'}])
    items = SubstackTopicsConnector(max_results=2).fetch()
    assert [x.title for x in items] == ['Latest', 'Older & useful']
    assert items[0].published_at == datetime(2026, 10, 25, 10, 30)
    assert items[0].summary == 'Public summary'
    assert items[0].url.endswith('/latest')


@patch('ai_news_radar.ingestion.substack.requests.get')
def test_changed_or_blocked_topic_page_is_a_failure_not_an_empty_success(get):
    get.return_value.text = '<html>Sign in or try again</html>'
    with pytest.raises(ValueError):
        SubstackTopicsConnector().fetch()
