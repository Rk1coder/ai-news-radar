"""Local cross-source event grouping; no network calls or generated news text."""
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from ai_news_radar.ingestion.base import strip_html

STOP = set('the a an and or of for with to in on at by from its is are as it this that your our their has have new next latest first ai model models introduces introduced introduce unveils unveiled unveil announces announced announce releases released release bir ve veya icin ile yeni bu su da de en daha olan olarak yapay zeka'.split())
VERSION = re.compile(r'\b([a-z][a-z0-9_-]{1,35}?)[\s_-]*v?(\d{1,4}(?:[.\-]\d{1,3}){0,3}[a-z]{0,2})\b')
EDITION = re.compile(r'^[\s_-]+((?:flash|pro|mini|nano|max|ultra|thinking|reasoning|coder|codex|lite|instruct|chat|base|vision|audio|omni|turbo|distill|super)(?:[\s_-]+(?:lite|mini|pro|thinking|instruct))?)\b')
NON_SUBJECTS = STOP | set('up under over than about saat gun yil day days hour hours year years million billion tokens percent top'.split())
EVENTS = {
    'security': ('vulnerab', 'security flaw', 'exploit', 'jailbreak', 'cve-', 'guvenlik acigi'),
    'pricing': ('pricing', 'price cut', 'prices', 'fiyat', 'api cost'),
    'funding': ('funding', 'raises ', 'investment', 'financing', 'yatirim', 'fonlama'),
    'acquisition': ('acquire', 'acquisition', 'satinal', 'satin al'),
    'benchmark': ('benchmark', 'compares', 'comparison', 'karsilastir'),
    'legal': ('lawsuit', 'sued', 'court', 'copyright', 'telif', 'dava'),
    'outage': ('outage', 'downtime', 'kesinti'),
    'patch': ('hotfix', 'patch ', 'bug fix', 'hata duzelt'),
    'deployment': ('deploys', 'adopts ', 'integrates', 'partnership', 'is birligi'),
}


@dataclass(frozen=True)
class DigestStory:
    primary: object
    related_sources: tuple = ()

    def __getattr__(self, key):
        return getattr(self.primary, key)


def _normalize(text):
    text = strip_html(text or '').casefold().replace('ı', 'i')
    return ''.join(char for char in unicodedata.normalize('NFKD', text) if not unicodedata.combining(char))


def _versions(text):
    anchors = set()
    for match in VERSION.finditer(text):
        name, version = match.groups()
        name = name.strip('_-').removesuffix('v').strip('_-')
        if name in NON_SUBJECTS or (version.isdigit() and 1900 <= int(version) <= 2100):
            continue
        edition = EDITION.match(text[match.end():])
        anchors.add((name, version.replace('-', '.'), re.sub(r'[\s_-]+', '-', edition.group(1)) if edition else ''))
    return anchors


def _terms(text):
    words = set(re.findall(r'[a-z]{2,}', text))
    words -= STOP
    words = {'run' if word in ('runs', 'running') else word for word in words}
    return {word[:-1] if len(word) > 4 and word.endswith('s') else word for word in words}


def _features(story):
    title = _normalize(story.raw_item.title)
    translated = _normalize(story.title_tr)
    body = _normalize(story.raw_item.summary) + ' ' + _normalize(story.summary_tr)
    versions = _versions(title) | _versions(translated)
    if not versions:
        # A headline may omit the version; the first model in its summary is
        # the subject. Incidental background models must not link two events.
        for sentence in re.split(r'(?<=[.!?])\s+', body):
            versions = _versions(sentence)
            if versions:
                break
    event_kinds = frozenset(kind for kind, markers in EVENTS.items() if any(marker in title or marker in translated for marker in markers))
    title_terms = _terms(title + ' ' + translated)
    weights = {word: 1.0 for word in title_terms}
    for word in _terms(body):
        weights.setdefault(word, 0.3)
    return versions, event_kinds, title_terms, weights


def _same_event(left, right, inverse_frequency):
    versions_a, kind_a, titles_a, words_a = left
    versions_b, kind_b, titles_b, words_b = right
    if kind_a != kind_b:
        return False
    if versions_a and versions_b:
        return bool(versions_a & versions_b)
    if len(titles_a & titles_b) < 3:
        return False
    dot = sum(weight * words_b.get(word, 0) * inverse_frequency[word] ** 2 for word, weight in words_a.items())
    norm_a = math.sqrt(sum((weight * inverse_frequency[word]) ** 2 for word, weight in words_a.items()))
    norm_b = math.sqrt(sum((weight * inverse_frequency[word]) ** 2 for word, weight in words_b.items()))
    return bool(norm_a and norm_b and dot / (norm_a * norm_b) >= 0.76)


def group_digest_stories(stories):
    features = [_features(story) for story in stories]
    frequency = Counter(word for feature in features for word in feature[3])
    inverse_frequency = {word: 1 + math.log((len(stories) + 1) / (count + 1)) for word, count in frequency.items()}
    groups = []
    for index, feature in enumerate(features):
        for group in groups:
            # Compare with the representative, not a chain of progressively
            # less similar articles that could absorb unrelated announcements.
            if _same_event(features[group[0]], feature, inverse_frequency):
                group.append(index)
                break
        else:
            groups.append([index])
    return [DigestStory(stories[group[0]], tuple(stories[index] for index in group[1:])) for group in groups]
