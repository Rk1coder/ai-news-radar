from datetime import UTC, datetime
from threading import Event, Thread

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.ingestion import active_connectors
from ai_news_radar.models import AppSettings, Base, CustomSource, ScanRun, SourceToggle
from ai_news_radar.scans import effective_settings, run_scan, scan_status
from ai_news_radar.scheduler import latest_slot, next_slot


def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'scan.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


class EmptySource:
    source_name = "healthy"
    source_type = "social"

    def fetch(self):
        return []


class BrokenSource(EmptySource):
    source_name = "broken"

    def fetch(self):
        raise RuntimeError("private provider detail")


def test_schedule_uses_istanbul_and_catches_only_latest_missed_slot(monkeypatch):
    monkeypatch.setattr("ai_news_radar.scheduler.SCAN_INTERVAL_MINUTES", 0)
    # 13:30 Istanbul -> 10:00 previous slot, 14:00 next.
    now = datetime(2026, 10, 26, 10, 30, tzinfo=UTC)
    assert latest_slot(now) == datetime(2026, 10, 26, 7, tzinfo=UTC)
    assert next_slot(now) == datetime(2026, 10, 26, 11, tzinfo=UTC)
    assert next_slot(datetime(2026, 10, 26, 19, tzinfo=UTC)) == datetime(2026, 10, 27, 3, tzinfo=UTC)
    assert latest_slot(datetime(2026, 10, 26, 0, tzinfo=UTC)) == datetime(2026, 10, 25, 19, tzinfo=UTC)


def test_scheduled_slot_is_not_repeated_after_restart_even_without_news(tmp_path):
    sessions = db(tmp_path)
    slot = datetime(2026, 10, 26, 7, tzinfo=UTC)
    first = run_scan(sessions, [EmptySource()], scheduled_for=slot)
    second = run_scan(sessions, [EmptySource()], scheduled_for=slot)
    assert first["status"] == "succeeded"
    assert first["new_count"] == 0
    assert second is None
    with sessions() as session:
        assert session.query(ScanRun).count() == 1
        state = scan_status(session)
        assert state["last_scan"]["finished_at"] is not None
        assert state["last_successful_at"] is not None


def test_partial_and_total_failure_do_not_claim_success(tmp_path):
    sessions = db(tmp_path)
    partial = run_scan(sessions, [EmptySource(), BrokenSource()])
    assert partial["status"] == "partial"
    assert partial["failed_sources"] == ["broken"]
    failed = run_scan(sessions, [BrokenSource()])
    assert failed["status"] == "failed"
    assert failed["successful_sources"] == 0
    assert "private" not in str(failed)


def test_manual_and_scheduled_scans_cannot_overlap(tmp_path):
    sessions = db(tmp_path)
    entered, release = Event(), Event()

    class SlowSource(EmptySource):
        def fetch(self):
            entered.set()
            assert release.wait(5)
            return []

    thread = Thread(target=lambda: run_scan(sessions, [SlowSource()]))
    thread.start()
    try:
        assert entered.wait(5)
        assert run_scan(sessions, [EmptySource()]) is None
        with sessions() as session:
            assert scan_status(session)["last_scan"]["status"] == "running"
    finally:
        release.set()
        thread.join(5)
    with sessions() as session:
        assert session.query(ScanRun).count() == 1


def test_orphaned_scan_is_marked_interrupted_and_can_be_retried(tmp_path):
    sessions = db(tmp_path)
    slot = datetime(2026, 10, 26, 7, tzinfo=UTC)
    with sessions() as session:
        session.add(ScanRun(status="running", scheduled_for=slot))
        session.commit()
    result = run_scan(sessions, [EmptySource()], scheduled_for=slot)
    assert result["status"] == "succeeded"
    with sessions() as session:
        assert session.query(ScanRun).order_by(ScanRun.id).first().status == "interrupted"


def test_interval_schedule_and_next_run(monkeypatch):
    import ai_news_radar.scheduler as scheduler
    monkeypatch.setattr(scheduler, 'SCAN_INTERVAL_MINUTES', 15, raising=False)
    now = datetime(2026, 10, 26, 14, 7, tzinfo=UTC)
    assert latest_slot(now) == datetime(2026, 10, 26, 14, 0, tzinfo=UTC)
    assert next_slot(now) == datetime(2026, 10, 26, 14, 15, tzinfo=UTC)
    assert next_slot(datetime(2026, 10, 26, 20, 59, tzinfo=UTC)) == datetime(2026, 10, 26, 21, 0, tzinfo=UTC)


def test_scan_status_reflects_db_backed_scan_interval(tmp_path):
    sessions = db(tmp_path)
    with sessions() as session:
        session.add(AppSettings(id=1, scan_interval_minutes=30, auto_scan_enabled=True))
        session.commit()
        settings = effective_settings(session)
        assert settings == {"interval_minutes": 30, "auto_scan_enabled": True}
        assert scan_status(session)["interval_minutes"] == 30


def test_active_connectors_excludes_disabled_and_includes_custom(tmp_path):
    sessions = db(tmp_path)
    with sessions() as session:
        session.add(SourceToggle(source_name="arxiv", enabled=False))
        session.add(CustomSource(name="my-feed", feed_url="https://example.com/feed.xml", source_type="media"))
        session.commit()
        names = {c.source_name for c in active_connectors(session)}
        assert "arxiv" not in names
        assert "my-feed" in names


def test_request_scan_returns_while_worker_runs_and_refuses_duplicate(tmp_path):
    from ai_news_radar.scans import request_scan
    sessions = db(tmp_path)
    release, entered = Event(), Event()
    class SlowSource(EmptySource):
        def fetch(self):
            entered.set()
            assert release.wait(5)
            return []
    try:
        result = request_scan(sessions, [EmptySource(), SlowSource()])
        assert result['status'] == 'running'
        assert entered.wait(2)
        with sessions() as session:
            assert scan_status(session)['last_scan']['successful_sources'] == 1
        assert request_scan(sessions, [EmptySource()]) is None
    finally:
        release.set()
