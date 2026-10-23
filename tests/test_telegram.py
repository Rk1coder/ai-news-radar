from unittest.mock import MagicMock, patch

from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.notifications.telegram import notify_telegram


def make_development():
    source = Source(name="arxiv", source_type="academic")
    raw_item = RawItem(
        source=source, external_id="x", title="Test baslik",
        url="http://example.com/x", summary="ozet",
    )
    development = Development(
        raw_item=raw_item, verified=True, priority_score=72,
        technical_impact_score=70, hype_score=60, applicability_score=80,
        sector_tags=["defense", "finance"],
    )
    return development


@patch("ai_news_radar.notifications.telegram.TELEGRAM_BOT_TOKEN", "")
@patch("ai_news_radar.notifications.telegram.TELEGRAM_CHAT_ID", "")
@patch("ai_news_radar.notifications.telegram.requests.post")
def test_notify_telegram_noop_without_config(mock_post):
    notify_telegram(make_development())
    mock_post.assert_not_called()


@patch("ai_news_radar.notifications.telegram.TELEGRAM_BOT_TOKEN", "dummy-token")
@patch("ai_news_radar.notifications.telegram.TELEGRAM_CHAT_ID", "-100123")
@patch("ai_news_radar.notifications.telegram.requests.post")
def test_notify_telegram_sends_formatted_message(mock_post):
    mock_post.return_value = MagicMock()

    notify_telegram(make_development())

    mock_post.assert_called_once()
    url, kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
    assert "dummy-token" in url
    payload = kwargs["json"]
    assert payload["chat_id"] == "-100123"
    assert "Test baslik" in payload["text"]
    assert "#72" in payload["text"]
