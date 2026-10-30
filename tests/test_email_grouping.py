from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.notifications import email
from ai_news_radar.notifications.email_grouping import group_digest_stories
from ai_news_radar.notifications.email_template import render_html, render_text


def article(index, title, source='publisher', summary='', title_tr=''):
    return Development(id=index,title_tr=title_tr or title,priority_score=90-index,raw_item=RawItem(
        id=index,external_id=str(index),title=title,summary=summary,
        url=f'https://{source}.example/news/{index}',published_at=datetime(2026,10,28,10),
        source=Source(name=source,source_type='company')))


@pytest.fixture(autouse=True)
def no_external_ai():
    with patch('anthropic.Anthropic',side_effect=AssertionError('No external model is needed')):
        yield


def genie_coverage():
    return [
        article(1,'Genie 4: A new generation of world simulation','deepmind','Genie 4: our new world model unlocking realism in real-time simulation.'),
        article(2,'DeepMind unveils Genie 4 world model promising realistic physics','ars','Genie 4 will roll out to developers soon.'),
        article(3,'Google’s next Genie AI model generates realistic experiences','verge','Google announced its Genie 4 world model for interactive experiences.'),
        article(4,"Google Deepmind’s Genie 4 puts a modern spin on agent designs",'decoder','Google introduced Genie 4, a world model that simulates interactive 3D worlds.'),
        article(5,'Google’s Genie 4 world model adds audio and real-time steering','techcrunch','Google DeepMind released Genie 4 in research preview.'),
        article(6,'Genie 4: Dünya simülasyonunda yeni nesil','turkish','Google DeepMind yeni dünya modelini duyurdu.'),
    ]


def test_same_event_coverage_is_one_item_with_all_sources_and_no_new_text():
    stories=genie_coverage()+[article(7,'Opera introduces local browser AI standard','other')]
    grouped=group_digest_stories(stories)
    assert len(grouped)==2
    assert grouped[0].title_tr==stories[0].title_tr
    assert grouped[0].related_sources==tuple(stories[1:6])
    html=render_html(grouped,'28.10.2026')
    plain=render_text(grouped,'28.10.2026')
    assert html.count('<h3 ')==2
    assert 'Diğer kaynaklar' in html
    assert all(story.raw_item.url in html and story.raw_item.url in plain for story in stories)


def test_same_company_or_model_is_not_enough_to_merge_distinct_announcements():
    stories=[article(1,'OpenAI releases Atlas 4','openai','Atlas 4 model is now available.'),
             article(2,'OpenAI changes Atlas 4 API pricing','openai','New API prices for Atlas 4.'),
             article(3,'Atlas 4 vulnerability exposes private prompts','security','Atlas 4 security exploit.'),
             article(4,'OpenAI releases Atlas 5','openai','New Atlas 5 model.')]
    grouped=group_digest_stories(stories)
    assert [story.id for story in grouped]==[1,2,3,4]


def test_same_unversioned_announcement_merges_but_broad_ai_topic_does_not():
    stories=[article(1,'Opera introduces WebAI standard for running local AI in the browser','a'),
             article(2,'Opera unveils WebAI standard to run local AI in your browser','b'),
             article(3,'Mozilla introduces AI form filling in Firefox browser','c')]
    grouped=group_digest_stories(stories)
    assert [story.id for story in grouped]==[1,3]
    assert grouped[0].related_sources==(stories[1],)


def test_empty_and_single_article_work_without_configuration():
    assert group_digest_stories([])==[]
    assert len(group_digest_stories([article(1,'Only story')]))==1


def test_model_editions_are_separate_launches():
    for first,second in [('Google launches Gemini 3 Flash','Google launches Gemini 3 Pro'),
                         ('OpenAI launches GPT-5.1 Codex','OpenAI launches GPT-5.1 Mini')]:
        assert len(group_digest_stories([article(1,first),article(2,second)]))==2


def test_model_version_spellings_and_numbered_product_names_normalize():
    for first,second in [('DeepSeek-V3 is released','DeepSeek V3 is announced'),
                         ('Introducing n8n 3.0','n8n 3.0 is released')]:
        assert len(group_digest_stories([article(1,first),article(2,second)]))==1


def test_digest_limit_applies_after_grouping_and_keeps_later_related_sources(sessions):
    now=datetime(2026,10,28,13,tzinfo=UTC)
    with sessions() as session:
        stories=genie_coverage()
        stories.insert(1,article(7,'Opera introduces local browser AI standard','other'))
        for i,story in enumerate(stories):
            story.verified=True
            story.priority_score=90-i
            session.add(story)
        session.commit()
        selected=email._top_stories(session,limit=2,now=now)
        assert [story.id for story in selected]==[1,7]
        assert len(selected[0].related_sources)==5


@pytest.fixture
def sessions(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from ai_news_radar.models import Base
    engine=create_engine(f'sqlite:///{tmp_path / "grouping.db"}')
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()
