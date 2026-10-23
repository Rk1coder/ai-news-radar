from unittest.mock import MagicMock, patch

import requests

from ai_news_radar.web.link_preview import extract_og_meta, fetch_link_preview

SAMPLE_HTML = """
<html><head>
<meta property="og:title" content="Bir Haber Basligi">
<meta content="https://example.com/image.jpg" property="og:image">
<meta name="description" content="Yedek aciklama">
</head></html>
"""


def test_extract_og_meta_handles_both_attribute_orders():
    meta = extract_og_meta(SAMPLE_HTML)
    assert meta["title"] == "Bir Haber Basligi"
    assert meta["image"] == "https://example.com/image.jpg"
    assert meta["description"] == "Yedek aciklama"


@patch("ai_news_radar.web.link_preview.requests.get")
def test_fetch_link_preview_returns_empty_on_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("network down")
    assert fetch_link_preview("https://example.com") == {}


@patch("ai_news_radar.web.link_preview.requests.get")
def test_fetch_link_preview_parses_response(mock_get):
    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    meta = fetch_link_preview("https://example.com")
    assert meta["image"] == "https://example.com/image.jpg"
