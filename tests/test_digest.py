from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.classification.digest import generate_weekly_digest
from ai_news_radar.models import Base, Development, RawItem, Source


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_no_recent_developments_skips_llm_call():
    session = make_session()

    with patch("ai_news_radar.classification.digest.Anthropic") as mock_anthropic:
        content, count = generate_weekly_digest(session)

    assert count == 0
    assert "bulunamadı" in content
    mock_anthropic.assert_not_called()


def test_summarizes_recent_verified_developments():
    session = make_session()
    source = Source(name="arxiv", source_type="academic", credibility_weight=0.9)
    session.add(source)
    session.flush()
    raw = RawItem(
        source_id=source.id, external_id="1", title="New model",
        url="http://example.com/1", published_at=datetime.now(UTC),
    )
    session.add(raw)
    session.flush()
    dev = Development(
        raw_item_id=raw.id, verified=True, priority_score=80,
        title_tr="Yeni model", sector_tags=["nlp"],
    )
    session.add(dev)
    session.commit()

    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Bu hafta önemli bir gelişme oldu.")]
    )
    with patch("ai_news_radar.classification.digest.Anthropic", return_value=mock_client):
        content, count = generate_weekly_digest(session)

    assert count == 1
    assert content == "Bu hafta önemli bir gelişme oldu."
    user_message = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Yeni model" in user_message
