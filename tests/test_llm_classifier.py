import json
from unittest.mock import Mock, patch

import pytest

from ai_news_radar.classification.llm_classifier import ClassificationResult, classify


def mock_anthropic(response_text):
    message = Mock(content=[Mock(text=response_text)])
    client = Mock()
    client.messages.create.return_value = message
    return patch("ai_news_radar.classification.llm_classifier.Anthropic", return_value=client), client


def test_classify_sends_title_and_summary_and_parses_response():
    payload = {
        "technical_impact_score": 70, "hype_score": 40, "applicability_score": 60,
        "sector_tags": ["defense", "healthcare"], "rationale": "Solid incremental work.",
        "title_tr": "Başlık", "summary_tr": "Özet",
    }
    patcher, client = mock_anthropic(json.dumps(payload))
    with patcher:
        result = classify("A new model", "It does things")

    assert result == ClassificationResult(
        technical_impact_score=70, hype_score=40, applicability_score=60,
        sector_tags=["defense", "healthcare"], rationale="Solid incremental work.",
        title_tr="Başlık", summary_tr="Özet",
    )
    _, kwargs = client.messages.create.call_args
    assert kwargs["messages"] == [{"role": "user", "content": "Baslik: A new model\n\nOzet: It does things"}]
    assert "0-100" in kwargs["system"]


def test_classify_strips_markdown_json_code_fence():
    payload = {"technical_impact_score": 10, "hype_score": 10, "applicability_score": 10,
               "sector_tags": [], "rationale": "r"}
    patcher, _ = mock_anthropic(f"```json\n{json.dumps(payload)}\n```")
    with patcher:
        result = classify("t", "s")
    assert result.technical_impact_score == 10


def test_classify_defaults_missing_translation_fields_to_empty_string():
    payload = {"technical_impact_score": 1, "hype_score": 2, "applicability_score": 3,
               "sector_tags": ["finance"], "rationale": "r"}
    patcher, _ = mock_anthropic(json.dumps(payload))
    with patcher:
        result = classify("t", "s")
    assert result.title_tr == ""
    assert result.summary_tr == ""


def test_classify_raises_on_malformed_json():
    patcher, client = mock_anthropic("not json at all")
    with patcher, pytest.raises(json.JSONDecodeError):
        classify("t", "s")
    assert client.messages.create.call_count == 2


def test_classify_retries_invalid_json_once_with_more_output_space():
    payload = {"technical_impact_score": 70, "hype_score": 40,
               "applicability_score": 60, "sector_tags": [], "rationale": "r",
               "title_tr": "Yeni model yayımlandı", "summary_tr": "Model sunuldu."}
    patcher, client = mock_anthropic('')
    client.messages.create.side_effect = [
        Mock(content=[Mock(text='{"summary_tr": "yarım')], stop_reason='max_tokens'),
        Mock(content=[Mock(text=json.dumps(payload))], stop_reason='end_turn'),
    ]
    with patcher:
        result = classify('t', 's')
    assert result.title_tr == payload['title_tr']
    assert [call.kwargs['max_tokens'] for call in client.messages.create.call_args_list] == [1024, 2048]


def test_classify_raises_on_missing_required_field():
    payload = {"technical_impact_score": 1, "hype_score": 2, "applicability_score": 3}
    patcher, _ = mock_anthropic(json.dumps(payload))
    with patcher, pytest.raises(KeyError):
        classify("t", "s")


def test_classify_propagates_api_errors():
    client = Mock()
    client.messages.create.side_effect = RuntimeError("api down")
    with patch("ai_news_radar.classification.llm_classifier.Anthropic", return_value=client):
        with pytest.raises(RuntimeError):
            classify("t", "s")


def test_priority_score_weights_technical_and_applicability_over_hype():
    result = ClassificationResult(
        technical_impact_score=80, hype_score=0, applicability_score=80,
        sector_tags=[], rationale="r",
    )
    assert result.priority_score == round(0.45 * 80 + 0.35 * 80 + 0.20 * 0)
