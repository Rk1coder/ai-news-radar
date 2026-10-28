from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_news_radar.classification.llm_classifier import ClassificationResult
from ai_news_radar.ingestion.base import FetchedItem
from ai_news_radar.models import Base, Development, WeeklyDigest
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
    session.add(WeeklyDigest(content="Test haftalık özeti", story_count=1))
    session.commit()
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


def test_search_finds_visible_translated_title_and_preserves_filters():
    SessionLocal = seeded_sessionmaker()
    with SessionLocal() as session:
        session.query(Development).first().title_tr = "Dünya Modellerini Eğitmek"
        session.commit()
    with patch("ai_news_radar.web.app.get_session", SessionLocal):
        client = TestClient(web_app_module.app)
        response = client.get("/api/developments", params={"q": "Dünya Modellerini"})
        assert len(response.json()["developments"]) == 1
        assert client.get("/api/developments", params={"q": "Dünya Modellerini", "sector": "healthcare"}).json()["developments"] == []
        assert len(client.get("/api/developments", params={"q": "Test gelisme"}).json()["developments"]) == 1


def test_today_filter_uses_istanbul_midnight_and_recent_default():
    from datetime import UTC, datetime, timedelta
    from zoneinfo import ZoneInfo
    from ai_news_radar.models import RawItem, Source

    sessions = seeded_sessionmaker()
    midnight = datetime.now(ZoneInfo("Europe/Istanbul")).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC).replace(tzinfo=None)
    with sessions() as session:
        source = session.query(Source).first()
        session.query(RawItem).first().published_at = midnight - timedelta(seconds=1)
        for key, when in [("first", midnight), ("newest", midnight + timedelta(minutes=1))]:
            raw = RawItem(source_id=source.id, external_id=key, title=key, url=f"https://example.com/{key}", published_at=when)
            session.add(raw)
            session.flush()
            session.add(Development(raw_item_id=raw.id, verified=True, priority_score=1))
        session.commit()
    with patch("ai_news_radar.web.app.get_session", sessions):
        client = TestClient(web_app_module.app)
        body = client.get("/api/developments?period=today").json()
        assert [d["raw_item"]["title"] for d in body["developments"]] == ["newest", "first"]
        assert len(client.get("/api/developments?period=all").json()["developments"]) == 3
        assert len(client.get("/api/developments?period=week").json()["developments"]) == 3


def test_feed_read_does_not_generate_missing_digest_or_contact_sources():
    sessions = seeded_sessionmaker()
    with sessions() as session:
        session.query(WeeklyDigest).delete()
        session.commit()
    with patch("ai_news_radar.web.app.get_session", sessions), patch(
        "ai_news_radar.classification.digest.generate_weekly_digest", side_effect=AssertionError("GET must be read-only")
    ):
        body = TestClient(web_app_module.app).get("/api/developments").json()
        assert body["weekly_digest"] is None
        assert body["scan_status"]["last_scan"] is None


def test_manual_refresh_reports_busy_instead_of_starting_duplicate():
    with patch("ai_news_radar.web.app.request_scan", return_value=None):
        response = TestClient(web_app_module.app).post("/api/refresh")
        assert response.status_code == 409


def search_sessions():
    from datetime import datetime, timedelta, UTC
    from ai_news_radar.models import RawItem, Source
    sessions = seeded_sessionmaker()
    with sessions() as session:
        session.query(Development).delete()
        session.query(RawItem).delete()
        source = session.query(Source).first()
        samples = [
            ('vision', 'Medical vision-language models', 'Ultrasound measurements.', '', ['healthcare'], True, 50),
            ('summary', 'New toolkit', 'Fast object detection for robots.', '', ['robotics'], True, 80),
            ('turkish', 'Yeni araç', '', 'GÖRÜNTÜ İŞLEME ile kalite kontrolü.', ['manufacturing'], True, 60),
            ('unrelated', 'Television provision', 'Financial division report.', '', ['finance'], True, 90),
            ('pending', 'Computer vision research', '', '', ['healthcare'], False, 100),
            ('language', 'New language model', 'Natural language processing for clinics.', '', ['healthcare'], True, 70),
        ]
        for i, (key, title, summary, summary_tr, tags, verified, priority) in enumerate(samples):
            raw = RawItem(source_id=source.id, external_id=key, title=title, url=f'https://example.com/{key}', summary=summary,
                          published_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2, minutes=i))
            session.add(raw)
            session.flush()
            session.add(Development(raw_item_id=raw.id, verified=verified, summary_tr=summary_tr, sector_tags=tags, priority_score=priority))
        session.commit()
    return sessions


def test_topic_search_finds_related_summaries_in_both_languages():
    sessions = search_sessions()
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        for term in ['bilgisayarlı görü', 'BİLGİSAYARLI GÖRÜ', 'bilgisayarli goru', 'computer vision', 'görüntü işleme']:
            body = client.get('/api/developments', params={'q': term, 'period': 'all'}).json()
            assert {d['raw_item']['url'].rsplit('/', 1)[-1] for d in body['developments']} == {'vision', 'summary', 'turkish'}, term
        body = client.get('/api/developments', params={'q': 'dogal dil isleme', 'period': 'all'}).json()
        assert [d['raw_item']['title'] for d in body['developments']] == ['New language model']


def test_search_requires_all_concepts_and_keeps_filters():
    sessions = search_sessions()
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        def results(**params):
            return client.get('/api/developments', params={'q': 'bilgisayarlı görü', 'period': 'all', **params}).json()['developments']
        assert [d['raw_item']['title'] for d in results(q='bilgisayarlı görü sağlık')] == ['Medical vision-language models']
        assert len(results(sector='healthcare', show_unverified='true')) == 2
        assert results(source_type='media') == []
        assert [d['raw_item']['title'] for d in results(min_priority=75)] == ['New toolkit']
        assert results(q='bilgisayarlı görü finans') == []
        assert results(q='%') == []
        assert results(q='_') == []
        assert len(results(q='  ')) == 5


def test_search_explains_archive_matches_without_changing_date_filter():
    sessions = search_sessions()
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        body = client.get('/api/developments', params={'q': 'bilgisayarlı görü', 'sector': 'healthcare', 'period': 'today'}).json()
        assert body['developments'] == []
        assert body['search']['archive_count'] == 1
        body = client.get('/api/developments', params={'q': 'bilgisayarlı görü', 'sector': 'finance', 'period': 'today'}).json()
        assert body['search']['archive_count'] == 0


def test_search_ranks_title_matches_first_but_respects_explicit_sort():
    sessions = search_sessions()
    with sessions() as session:
        from ai_news_radar.models import RawItem
        session.query(RawItem).filter_by(external_id='summary').one().title = 'Computer vision toolkit'
        session.commit()
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        params = {'q': 'computer vision', 'period': 'all'}
        assert client.get('/api/developments', params=params).json()['developments'][0]['raw_item']['title'] == 'Computer vision toolkit'
        assert client.get('/api/developments', params={**params, 'sort': 'recent'}).json()['developments'][0]['raw_item']['title'] == 'Medical vision-language models'


def test_every_displayed_turkish_sector_can_be_searched_without_title_match():
    sessions = seeded_sessionmaker()
    labels = {
        'advertising': 'Reklam', 'autonomous_systems': 'Otonom sistemler',
        'cybersecurity': 'Siber güvenlik', 'defense': 'Savunma', 'design': 'Tasarım',
        'e-commerce': 'E-ticaret', 'education': 'Eğitim', 'enterprise': 'Kurumsal',
        'entertainment': 'Eğlence', 'finance': 'Finans', 'general_software': 'Yazılım',
        'government': 'Kamu', 'healthcare': 'Sağlık', 'manufacturing': 'Üretim',
        'marketing': 'Pazarlama', 'robotics': 'Robotik', 'nlp': 'Dil işleme',
    }
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        for tag, label in labels.items():
            with sessions() as session:
                session.query(Development).one().sector_tags = [tag]
                session.commit()
            results = client.get('/api/developments', params={'q': label, 'period': 'all'}).json()['developments']
            assert len(results) == 1, (tag, label)


def test_default_feed_includes_latest_news_even_when_no_publications_today():
    sessions = search_sessions()
    with patch('ai_news_radar.web.app.get_session', sessions):
        client = TestClient(web_app_module.app)
        body = client.get('/api/developments').json()
        assert len(body['developments']) == 5
        assert body['developments'][0]['raw_item']['title'] == 'Medical vision-language models'
        assert client.get('/api/developments?period=today').json()['developments'] == []


def empty_sessionmaker():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_settings_scan_update_round_trips():
    sessions = empty_sessionmaker()
    with patch("ai_news_radar.web.app.get_session", sessions):
        client = TestClient(web_app_module.app)
        before = client.get("/api/settings").json()
        assert before["scan"]["interval_minutes"] == 15
        updated = client.put("/api/settings/scan", json={"interval_minutes": 30, "auto_scan_enabled": False})
        assert updated.status_code == 200
        want = {**before["scan"], "interval_minutes": 30, "auto_scan_enabled": False}
        assert updated.json()["scan"] == want
        assert client.get("/api/settings").json()["scan"] == want
        assert client.put("/api/settings/scan", json={"interval_minutes": 7}).status_code == 400


def test_settings_source_toggle_round_trips():
    sessions = empty_sessionmaker()
    with patch("ai_news_radar.web.app.get_session", sessions):
        client = TestClient(web_app_module.app)
        names = {s["name"] for s in client.get("/api/settings").json()["sources"]}
        name = next(iter(names))
        off = client.put(f"/api/settings/sources/{name}", json={"enabled": False})
        assert off.status_code == 200
        row = next(s for s in off.json()["sources"] if s["name"] == name)
        assert row["enabled"] is False
        assert client.put("/api/settings/sources/not-a-real-source", json={"enabled": False}).status_code == 404


def test_settings_custom_source_add_and_remove_round_trips():
    sessions = empty_sessionmaker()
    with patch("ai_news_radar.web.app.get_session", sessions):
        client = TestClient(web_app_module.app)
        created = client.post(
            "/api/settings/sources/custom",
            json={"name": "my-feed", "feed_url": "https://example.com/feed.xml", "source_type": "media"},
        )
        assert created.status_code == 201
        custom = [s for s in created.json()["sources"] if not s["builtin"]]
        assert custom == [{"id": custom[0]["id"], "name": "my-feed", "feed_url": "https://example.com/feed.xml",
                            "source_type": "media", "enabled": True, "builtin": False}]
        dup = client.post(
            "/api/settings/sources/custom",
            json={"name": "my-feed", "feed_url": "https://example.com/other.xml", "source_type": "media"},
        )
        assert dup.status_code == 409
        bad = client.post(
            "/api/settings/sources/custom",
            json={"name": "bad", "feed_url": "not-a-url", "source_type": "media"},
        )
        assert bad.status_code == 400
        removed = client.delete(f"/api/settings/sources/custom/{custom[0]['id']}")
        assert removed.status_code == 200
        assert [s for s in removed.json()["sources"] if not s["builtin"]] == []
        assert client.delete("/api/settings/sources/custom/999").status_code == 404
