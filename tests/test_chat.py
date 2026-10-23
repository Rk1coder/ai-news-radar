from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.classification.chat import answer_question
from ai_news_radar.models import Base, Development, RawItem, Source


def make_development(verified=True):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    source = Source(name="arxiv", source_type="academic", credibility_weight=0.9)
    session.add(source)
    session.flush()
    raw = RawItem(
        source_id=source.id, external_id="1", title="New model", url="http://example.com/1",
        summary="ozet", published_at=datetime.now(UTC),
    )
    session.add(raw)
    session.flush()
    dev = Development(
        raw_item_id=raw.id, verified=verified, priority_score=70 if verified else None,
        title_tr="Yeni model", summary_tr="Yeni modelin ozeti",
        classification_rationale="Onemli bir katki", technical_impact_score=70,
        hype_score=50, applicability_score=60, sector_tags=["nlp"],
        verification_notes="dogrulanamadi" if not verified else "",
    )
    session.add(dev)
    session.commit()
    dev.raw_item.source  # relationships touched while session is alive
    return session, dev


@patch("ai_news_radar.classification.chat.requests.get")
@patch("ai_news_radar.classification.chat.Anthropic")
def test_answer_question_grounds_in_context(mock_anthropic, mock_get):
    mock_get.side_effect = requests.ConnectionError("fetch disabled for test")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Bu model NLP gorevleri icin kullaniliyor.")]
    )
    mock_anthropic.return_value = mock_client

    _session, dev = make_development(verified=True)
    answer = answer_question(dev, "Bu model ne ise yariyor?")

    assert answer == "Bu model NLP gorevleri icin kullaniliyor."
    context_message = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Yeni model" in context_message
    assert "Onemli bir katki" in context_message


@patch("ai_news_radar.classification.chat.requests.get")
@patch("ai_news_radar.classification.chat.Anthropic")
def test_answer_question_passes_history(mock_anthropic, mock_get):
    mock_get.side_effect = requests.ConnectionError("fetch disabled for test")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="cevap")])
    mock_anthropic.return_value = mock_client

    _session, dev = make_development(verified=True)
    answer_question(
        dev, "ikinci soru",
        history=[{"role": "user", "content": "ilk soru"}, {"role": "assistant", "content": "ilk cevap"}],
    )

    messages = mock_client.messages.create.call_args.kwargs["messages"]
    roles_and_content = [(m["role"], m["content"]) for m in messages]
    assert ("user", "ilk soru") in roles_and_content
    assert ("assistant", "ilk cevap") in roles_and_content
    assert ("user", "ikinci soru") in roles_and_content
