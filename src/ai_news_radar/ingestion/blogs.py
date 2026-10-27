"""Public blog metadata for publishers without an RSS feed. No login or JS execution."""
import json
from datetime import UTC, datetime
from html import unescape
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from ai_news_radar.ingestion.base import FetchedItem, strip_html
from ai_news_radar.ingestion.rss import USER_AGENT, select_recent


def read_page(url):
    response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


def clean(value):
    return ' '.join(unescape(strip_html(value or '')).split())


def article_url(value, page_url):
    if not isinstance(value, str) or not value:
        return None
    url = urljoin(page_url, value)
    parsed, origin = urlsplit(url), urlsplit(page_url)
    if parsed.scheme not in ('http', 'https') or parsed.netloc != origin.netloc:
        return None
    return parsed._replace(query='', fragment='').geturl()


def jsonld_items(soup, page_url):
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    items = {}
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            # Make emits literal newlines inside some description strings.
            payload = json.loads(script.string or script.get_text(), strict=False)
        except (ValueError, TypeError):
            continue  # Some publishers include unrelated, malformed organization metadata.
        for post in walk(payload):
            types = post.get('@type', [])
            types = [types] if isinstance(types, str) else types
            if not any(t in ('BlogPosting', 'Article', 'NewsArticle') for t in types):
                continue
            url = article_url(post.get('url'), page_url)
            title, date = post.get('headline'), post.get('datePublished')
            if not url or not isinstance(title, str) or not isinstance(date, str):
                continue
            try:
                published = datetime.fromisoformat(date.replace('Z', '+00:00'))
                published = published.replace(tzinfo=UTC) if published.tzinfo is None else published
                published = published.astimezone(UTC).replace(tzinfo=None)
            except ValueError:
                continue
            items[url] = FetchedItem(url, clean(title), url, clean(post.get('description'))[:6000], published)
    return list(items.values())


class JsonLdBlogConnector:
    source_type = 'company'

    def __init__(self, source_name, page_url, max_results=50, *, lookback_days=4, latest_fallback=1):
        self.source_name = source_name
        self.page_url = page_url
        self.max_results = max_results
        self.lookback_days = lookback_days
        self.latest_fallback = latest_fallback

    def select(self, items):
        if not items:
            raise ValueError(f'{self.source_name}: no usable public article metadata')
        return select_recent(items, self.max_results, self.lookback_days, self.latest_fallback)

    def fetch(self):
        return self.select(jsonld_items(read_page(self.page_url), self.page_url))


class MakeBlogConnector(JsonLdBlogConnector):
    def __init__(self, *, lookback_days=4):
        super().__init__('make-blog', 'https://www.make.com/blog', lookback_days=lookback_days)

    def fetch(self):
        soup = read_page(self.page_url)
        links = []
        for link in soup.select('a[href]'):
            url = article_url(link.get('href'), self.page_url)
            if url and urlsplit(url).path.startswith('/blog/') and url not in links:
                links.append(url)
        items = {}
        # Bounded requests: featured + newest articles in the public listing.
        for url in links[:20]:
            posts = jsonld_items(read_page(url), self.page_url)
            if not posts:
                raise ValueError('Make article metadata is missing')
            for item in posts:
                items[item.url] = item
        return self.select(list(items.values()))


class DogusBlogConnector(JsonLdBlogConnector):
    def __init__(self, *, lookback_days=4):
        super().__init__('dogus-teknoloji-blog', 'https://www.d-teknoloji.com.tr/tr/blog',
                         lookback_days=lookback_days)

    def fetch(self):
        soup = read_page(self.page_url)
        months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        items = {}
        for card in soup.select('.clickable-card[data-url]'):
            title = card.select_one('h2, h5')
            date = card.select_one('.source-list__item-time')
            summary = card.select_one('.card-text, .source-list__top-main--desc')
            url = article_url(card.get('data-url'), self.page_url)
            if not title or not date or not url:
                continue
            try:
                day, month, year = date.get_text(' ', strip=True).split('|')[0].split()
                published = datetime(int(year), months.index(month) + 1, int(day),
                                     tzinfo=ZoneInfo('Europe/Istanbul')).astimezone(UTC).replace(tzinfo=None)
            except (ValueError, TypeError):
                continue
            items[url] = FetchedItem(url, title.get_text(' ', strip=True), url,
                                    summary.get_text(' ', strip=True) if summary else '', published)
        return self.select(list(items.values()))
