from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.classification.llm_classifier import ClassificationResult
from ai_news_radar.ingestion.base import FetchedItem
from ai_news_radar.models import Base
from ai_news_radar.pipeline import run_pipeline


class FakeAcademicConnector:
    source_name = "fake-academic"
    source_type = "academic"

    def fetch(self):
        return [
            FetchedItem(
                external_id="abc-1",
                title="Yeni bir model mimarisi",
                url="http://example.com/abc-1",
                summary="Ozet",
                published_at=datetime(2025, 1, 1),
            )
        ]


class FakeSocialConnector:
    source_name = "fake-social"
    source_type = "social"

    def fetch(self):
        return [
            FetchedItem(
                external_id="post-1",
                title="Viral paylasim",
                url="http://example.com/post-1",
                summary="Iddiali ama teyitsiz",
                published_at=None,
            )
        ]


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@patch("ai_news_radar.pipeline.classify")
def test_academic_item_gets_classified(mock_classify):
    mock_classify.return_value = ClassificationResult(
        technical_impact_score=80,
        hype_score=40,
        applicability_score=60,
        sector_tags=["general_software"],
        rationale="test",
    )
    session = make_session()

    developments = run_pipeline(session, [FakeAcademicConnector()])

    assert len(developments) == 1
    dev = developments[0]
    assert dev.verified is True
    assert dev.priority_score == round(0.45 * 80 + 0.35 * 60 + 0.20 * 40)
    mock_classify.assert_called_once()


@patch("ai_news_radar.pipeline.classify")
def test_social_item_is_not_classified_without_cross_verification(mock_classify):
    session = make_session()

    developments = run_pipeline(session, [FakeSocialConnector()])

    assert len(developments) == 1
    dev = developments[0]
    assert dev.verified is False
    assert dev.technical_impact_score is None
    mock_classify.assert_not_called()


@patch("ai_news_radar.pipeline.classify")
def test_rerunning_pipeline_does_not_duplicate_raw_items(mock_classify):
    mock_classify.return_value = ClassificationResult(
        technical_impact_score=50, hype_score=50, applicability_score=50,
        sector_tags=[], rationale="",
    )
    session = make_session()
    connector = FakeAcademicConnector()

    first_run = run_pipeline(session, [connector])
    second_run = run_pipeline(session, [connector])

    assert len(first_run) == 1
    assert len(second_run) == 0


@patch("ai_news_radar.pipeline.classify")
def test_notifier_called_only_for_verified_developments(mock_classify):
    mock_classify.return_value = ClassificationResult(
        technical_impact_score=80, hype_score=40, applicability_score=60,
        sector_tags=["general_software"], rationale="test",
    )
    session = make_session()
    notified = []

    run_pipeline(session, [FakeAcademicConnector(), FakeSocialConnector()], notifier=notified.append)

    assert len(notified) == 1
    assert notified[0].raw_item.external_id == "abc-1"
