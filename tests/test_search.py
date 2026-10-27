from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.search import NewsSearch, normalize


def make_development(title='', summary='', title_tr='', summary_tr='', sector_tags=None, source_name='arxiv'):
    source = Source(name=source_name, source_type='academic')
    raw = RawItem(source=source, external_id='x', title=title, url='https://example.com/x', summary=summary)
    return Development(raw_item=raw, title_tr=title_tr, summary_tr=summary_tr, sector_tags=sector_tags or [])


def test_normalize_strips_punctuation_case_and_turkish_dotless_i():
    assert normalize('YOLO: Object-Detection!!') == 'yolo object detection'
    assert normalize('Görüntü İşleme') == 'goruntu isleme'


def test_empty_query_scores_zero_and_filters_everything_out():
    search = NewsSearch('')
    development = make_development(title='Anything at all')
    assert search.score(development) == 0
    assert search.filter([development]) == []


def test_no_match_is_excluded():
    search = NewsSearch('quantum computing')
    development = make_development(title='A piece about cooking recipes')
    assert search.score(development) == 0
    assert search.filter([development]) == []


def test_plain_keyword_matches_title():
    search = NewsSearch('robot')
    development = make_development(title='New robot learns to walk')
    assert search.score(development) > 0


def test_every_query_word_is_required_not_just_any():
    search = NewsSearch('robot healthcare')
    only_robot = make_development(title='A new robot')
    both = make_development(title='A new robot', summary='used in healthcare settings')
    assert search.score(only_robot) == 0
    assert search.score(both) > 0


def test_word_boundary_prevents_substring_false_positive():
    # 'vision' must not match inside 'television', per phrase_pattern's design.
    search = NewsSearch('vision')
    development = make_development(title='A new television launched today')
    assert search.score(development) == 0


def test_turkish_english_concept_alias_matches_related_document_terms():
    # Query uses the Turkish alias for computer vision; document only uses an
    # English related term from the same topic group.
    search = NewsSearch('bilgisayarlı görü')
    development = make_development(title='New object detection model released')
    assert search.score(development) > 0


def test_longest_alias_wins_over_shorter_overlapping_alias():
    # 'doğal dil işleme' should not be chopped up by the shorter 'dil işleme'-like
    # alias matching; querying the full phrase should match NLP-topic documents.
    search = NewsSearch('doğal dil işleme')
    development = make_development(title='New machine translation system announced')
    assert search.score(development) > 0


def test_exact_phrase_match_scores_higher_than_related_term_only():
    exact_query = NewsSearch('object detection')
    exact_hit = make_development(title='A breakthrough in object detection models')
    related_only = make_development(title='A new yolo based system')
    assert exact_query.score(exact_hit) > exact_query.score(related_only)


def test_sector_tags_and_source_name_are_searchable_fields():
    search = NewsSearch('healthcare')
    development = make_development(title='Unrelated title', sector_tags=['healthcare'])
    assert search.score(development) > 0

    search = NewsSearch('arxiv')
    development = make_development(title='Unrelated title', source_name='arxiv')
    assert search.score(development) > 0


def test_filter_with_relevance_sorts_by_descending_score():
    search = NewsSearch('robot')
    weak = make_development(title='unrelated', summary='a robot is mentioned here')
    strong = make_development(title='robot', summary='unrelated summary')
    results = search.filter([weak, strong], relevance=True)
    assert results[0] is strong
    assert results[1] is weak
