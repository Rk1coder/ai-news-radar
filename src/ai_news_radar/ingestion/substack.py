"""Read public article metadata from Substack's AI topic page, without login."""
import json
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from ai_news_radar.ingestion.base import FetchedItem, strip_html
from ai_news_radar.ingestion.rss import USER_AGENT


class _PreloadsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = dict(attrs).get('id') == 'preloads-json'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


class SubstackTopicsConnector:
    source_name = 'substack-ai'
    source_type = 'media'
    page_url = 'https://substack.com/topics/ai'

    def __init__(self, max_results=15):
        self.max_results = max_results

    def fetch(self):
        response = requests.get(self.page_url, headers={'User-Agent': USER_AGENT}, timeout=30)
        response.raise_for_status()
        parser = _PreloadsParser()
        parser.feed(response.text)
        payload = json.loads(''.join(parser.parts))
        posts = payload.get('posts')
        if not isinstance(posts, list):
            raise ValueError('Substack topic article metadata is missing')
        items, seen = [], set()
        for post in posts:
            if not isinstance(post, dict):
                continue
            url = post.get('canonical_url', '')
            title, date = post.get('title'), post.get('post_date')
            if not isinstance(url, str) or urlparse(url).scheme not in ('http', 'https') or not urlparse(url).hostname:
                continue
            if not title or not date or url in seen:
                continue
            try:
                published = datetime.fromisoformat(date.replace('Z', '+00:00'))
                if published.tzinfo is None:
                    continue
                published = published.astimezone(UTC).replace(tzinfo=None)
            except (ValueError, TypeError):
                continue
            summary = post.get('subtitle') or post.get('description') or post.get('truncated_body_text') or ''
            items.append(FetchedItem(external_id=url, title=unescape(strip_html(title)).strip(),
                                     url=url, summary=unescape(strip_html(summary)).strip()[:6000],
                                     published_at=published))
            seen.add(url)
        if posts and not items:
            raise ValueError('Substack topic contained no usable articles')
        return sorted(items, key=lambda item: item.published_at, reverse=True)[:self.max_results]
