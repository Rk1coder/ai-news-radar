from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_news_radar.classification.llm_classifier import ClassificationResult
from ai_news_radar.ingestion.base import FetchedItem
from ai_news_radar.models import Base
from ai_news_radar.pipeline import run_pipeline
from ai_news_radar.web import app as web_app_module


class FakeConnector:
    source_name = "fake-academic"
    source_type = "academic"

    def fetch(self):
        return [
            FetchedItem(
                external_id="x-1", title="Test gelisme", url="http://example.com/x-1",
                summary="ozet", published_at=None,
            )
        ]


def seeded_sessionmaker():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    with patch("ai_news_radar.pipeline.classify") as mock_classify:
        mock_classify.return_value = ClassificationResult(
            technical_impact_score=70, hype_score=40, applicability_score=60,
            sector_tags=["defense"], rationale="test",
        )
        run_pipeline(session, [FakeConnector()])
    session.close()
    return SessionLocal


def test_api_returns_developments():
    SessionLocal = seeded_sessionmaker()
    with patch("ai_news_radar.web.app.get_session", SessionLocal):
        client = TestClient(web_app_module.app)
        response = client.get("/api/developments")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    titles = [d["raw_item"]["title"] for d in body["developments"]]
    assert "Test gelisme" in titles


def test_api_sector_filter_excludes_non_matching():
    SessionLocal = seeded_sessionmaker()
    with patch("ai_news_radar.web.app.get_session", SessionLocal):
        client = TestClient(web_app_module.app)
        response = client.get("/api/developments", params={"sector": "healthcare"})

    assert response.status_code == 200
    assert response.json()["developments"] == []
