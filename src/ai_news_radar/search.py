"""Small-archive topic retrieval without remote calls or a database extension.

Aliases recognize a query topic; related terms broaden that topic's documents,
not every narrower query. Keep acronyms bounded to avoid incidental matches.
"""
import re
import unicodedata


def normalize(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.casefold().replace('ı', 'i'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


# (query aliases, additional document terms). No recursive expansion.
TOPICS = (
    (('bilgisayarlı görü', 'computer vision', 'görüntü işleme', 'image processing'),
     ('vision language', 'vision encoder', 'visual recognition', 'image recognition',
      'object detection', 'nesne tespiti', 'nesne algılama', 'image segmentation',
      'görüntü segmentasyonu', 'görüntü analizi', 'image analysis', 'vlm', 'vlms')),
    (('nesne tespiti', 'nesne algılama', 'object detection'), ('yolo',)),
    (('doğal dil işleme', 'dil işleme', 'natural language processing', 'nlp'),
     ('machine translation', 'makine çevirisi', 'text classification', 'sentiment analysis')),
    (('büyük dil modeli', 'büyük dil modelleri', 'large language model', 'llm', 'llms'), ()),
    (('robotik', 'robotics', 'robot'), ('robotic', 'robots')),
    (('sağlık', 'healthcare', 'tıp', 'medical'), ('clinical', 'tıbbi', 'klinik')),
    (('siber güvenlik', 'cybersecurity'), ('cyber security', 'malware', 'zararlı yazılım')),
    (('pekiştirmeli öğrenme', 'pekiştirme öğrenmesi', 'reinforcement learning'), ()),
    (('derin öğrenme', 'deep learning'), ('neural network', 'sinir ağı')),
    (('makine öğrenmesi', 'machine learning'), ()),
    (('üretken yapay zeka', 'generative ai'), ('generative artificial intelligence',)),
    (('konuşma tanıma', 'speech recognition', 'speech to text'), ('ses tanıma',)),
    (('otonom sistemler', 'autonomous systems'), ('autonomous driving', 'otonom sürüş')),
    (('finans', 'finance'), ('financial',)),
    (('eğitim', 'education'), ('educational',)),
    (('savunma', 'defense', 'defence'), ()),
    (('üretim', 'manufacturing'), ()),
    (('yazılım', 'software'), ('general software',)),
    (('reklam', 'advertising'), ()),
    (('tasarım', 'design'), ()),
    (('e ticaret', 'e commerce', 'ecommerce'), ()),
    (('kurumsal', 'enterprise'), ()),
    (('eğlence', 'entertainment'), ('media entertainment',)),
    (('kamu', 'government'), ()),
    (('pazarlama', 'marketing'), ()),
)


def phrase_pattern(phrase: str, *, suffix: bool = False) -> re.Pattern:
    words = normalize(phrase).split()
    # Prefix at a word boundary tolerates inflected words, but never 'vision'
    # inside 'television'. Short acronyms require a complete token.
    end = r'[a-z0-9]*\b' if suffix and len(words[-1]) >= 4 else r'\b'
    return re.compile(r'\b' + r'\s+'.join(map(re.escape, words)) + end)


class NewsSearch:
    def __init__(self, query: str):
        self.query = normalize(query)
        self.exact = phrase_pattern(self.query) if self.query else None
        remaining = self.query
        self.units: list[list[re.Pattern]] = []
        # Longest phrases first so 'dil işleme' cannot eat 'doğal dil işleme'.
        aliases = sorted(
            ((normalize(alias), group) for group in TOPICS for alias in group[0]),
            key=lambda entry: len(entry[0]), reverse=True,
        )
        matched_groups = set()
        for alias, group in aliases:
            pattern = phrase_pattern(alias)
            if pattern.search(remaining):
                remaining = pattern.sub(' ', remaining)
                if group not in matched_groups:
                    self.units.append([phrase_pattern(term, suffix=True) for term in (*group[0], *group[1])])
                    matched_groups.add(group)
        self.units.extend([phrase_pattern(word, suffix=True)] for word in remaining.split())

    def score(self, development) -> int:
        if not self.units:
            return 0
        raw = development.raw_item
        fields = [
            (normalize(development.title_tr or ''), 8),
            (normalize(raw.title or ''), 8),
            (normalize(development.summary_tr or ''), 3),
            (normalize(raw.summary or ''), 3),
            (normalize(' '.join(development.sector_tags or [])), 4),
            (normalize(raw.source.name or ''), 2),
        ]
        score = 0
        for alternatives in self.units:
            match = max((weight for field, weight in fields if any(p.search(field) for p in alternatives)), default=0)
            if not match:
                return 0  # Every query concept is required.
            score += match
        # Prefer the user's own phrase over a related-term title match.
        return score + max((weight for field, weight in fields if self.exact.search(field)), default=0)

    def filter(self, developments, *, relevance: bool = False):
        matches = [(d, self.score(d)) for d in developments]
        matches = [(d, score) for d, score in matches if score]
        if relevance:
            matches.sort(key=lambda pair: pair[1], reverse=True)
        return [d for d, _ in matches]
