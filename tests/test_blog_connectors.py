import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


def response(text):
    r = MagicMock()
    r.text = text
    return r


def article(url='https://atalay.tech/blog/new', date='2026-10-23T12:00:00+03:00'):
    return {'@type': 'BlogPosting', 'headline': 'AI &amp; agents', 'url': url,
            'description': '<p>Local models</p>', 'datePublished': date,
            'dateModified': '2026-10-26T15:00:00Z'}


@patch('ai_news_radar.ingestion.blogs.requests.get')
def test_jsonld_blog_reads_nested_posts_and_preserves_publication_date(get):
    from ai_news_radar.ingestion.blogs import JsonLdBlogConnector
    get.return_value = response('<script type="application/ld+json">' + json.dumps({
        '@type': 'Blog', 'blogPost': [article(), article(), article('javascript:bad'),
                                    article('https://other.example/blog/unrelated')]}) + '</script>')
    items = JsonLdBlogConnector('atalay-tech', 'https://atalay.tech/blog', lookback_days=None).fetch()
    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 10, 23, 9)
    assert items[0].title == 'AI & agents'
    assert items[0].summary == 'Local models'


@patch('ai_news_radar.ingestion.blogs.requests.get')
def test_make_follows_only_same_host_article_links_and_deduplicates(get):
    from ai_news_radar.ingestion.blogs import MakeBlogConnector
    get.side_effect = [response('''<a href="/blog/new">New</a><a href="/blog/new">Repeat</a>
        <a href="https://other.example/blog/steal">External</a><a href="/contact">Contact</a>'''),
        response('<script type="application/ld+json">' + json.dumps(article('https://www.make.com/blog/new')) + '</script>')]
    items = MakeBlogConnector(lookback_days=None).fetch()
    assert len(items) == 1
    assert items[0].url == 'https://www.make.com/blog/new'


@patch('ai_news_radar.ingestion.blogs.requests.get')
def test_dogus_visible_cards_parse_turkish_date_and_skip_image_only_cards(get):
    from ai_news_radar.ingestion.blogs import DogusBlogConnector
    get.return_value = response('''
        <div class="clickable-card" data-url="/tr/blog/agents"><img src="pic"></div>
        <div class="clickable-card" data-url="/tr/blog/agents">
          <h2>Yapay zekâ ajanları</h2><p class="source-list__top-main--desc">Bir rehber</p>
          <p class="source-list__item-time">23 Ekim 2026 | 6 dk</p>
        </div>''')
    items = DogusBlogConnector(lookback_days=None).fetch()
    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 10, 22, 21)
    assert items[0].summary == 'Bir rehber'


@patch('ai_news_radar.ingestion.blogs.requests.get')
def test_missing_blog_metadata_is_reported_as_failure(get):
    from ai_news_radar.ingestion.blogs import JsonLdBlogConnector
    get.return_value = response('<html>Sign in</html>')
    with pytest.raises(ValueError):
        JsonLdBlogConnector('atalay-tech', 'https://atalay.tech/blog').fetch()


@patch('ai_news_radar.ingestion.blogs.requests.get')
def test_publisher_jsonld_with_literal_newline_in_description(get):
    from ai_news_radar.ingestion.blogs import JsonLdBlogConnector
    payload = json.dumps(article()).replace('Local models', 'Local\nmodels')
    get.return_value = response('<script type="application/ld+json">' + payload + '</script>')
    items = JsonLdBlogConnector('atalay-tech', 'https://atalay.tech/blog', lookback_days=None).fetch()
    assert items[0].summary == 'Local models'
