"""Custom scan rules: API persistence, validation and real scheduler consumers."""
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_news_radar.models import Base
from ai_news_radar.scans import effective_settings, scan_status
from ai_news_radar.scheduler import latest_slot, next_slot, slots_near
from ai_news_radar.web import app as web_app


@pytest.fixture
def sessions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


@pytest.fixture
def client(sessions):
    with patch("ai_news_radar.web.app.get_session", sessions):
        yield TestClient(web_app.app)


def test_program_defaults_to_configured_hours_without_changing_app_settings_schema(client, sessions):
    scan = client.get("/api/settings").json()["scan"]
    assert scan["program"] == {"times": ["06:00", "10:00", "14:00", "18:00", "22:00"], "windows": []}
    assert scan["timezone"] == "Europe/Istanbul"
    with sessions() as session:
        assert {c["name"] for c in inspect(session.get_bind()).get_columns("app_settings")} == {
            "id", "scan_interval_minutes", "auto_scan_enabled",
        }


def test_program_normalizes_and_persists_across_sessions_and_mode_changes(client, sessions):
    window = {"start": "22:00", "end": "01:00", "interval_minutes": 30}
    program = {"times": ["13:30", "09:00", "09:00"], "windows": [window, window]}
    result = client.put("/api/settings/scan", json={"interval_minutes": 0, "program": program})
    assert result.status_code == 200
    want = {"times": ["09:00", "13:30"], "windows": [window]}
    assert result.json()["scan"]["program"] == want
    client.put("/api/settings/scan", json={"interval_minutes": 15})
    with sessions() as session:
        assert effective_settings(session)["program"] == want
    assert client.put("/api/settings/scan", json={"interval_minutes": 0}).json()["scan"]["program"] == want


@pytest.mark.parametrize("program", [
    None, [], {"times": "09:00", "windows": []}, {"times": ["9:00"], "windows": []},
    {"times": ["24:00"], "windows": []}, {"times": [900], "windows": []},
    {"times": ["09:00\n"], "windows": []}, {"times": [], "windows": None},
    {"times": ["09:00"] * 49, "windows": []},
    {"times": [], "windows": [{"start": "09:00", "end": "09:00", "interval_minutes": 15}]},
    {"times": [], "windows": [{"start": "09:00", "end": "18:00", "interval_minutes": 7}]},
    {"times": [], "windows": [{"start": "09:00", "end": "18:00", "interval_minutes": "15"}]},
    {"times": [], "windows": [{"start": "09:00", "end": "18:00", "interval_minutes": True}]},
    {"times": [], "windows": [{"start": "09:00", "end": "18:00"}]},
    {"times": [], "windows": ["09:00-18:00"]},
    {"times": [], "windows": [{"start": "09:00", "end": "18:00", "interval_minutes": 15}] * 13},
    {"times": [], "windows": []},
])
def test_invalid_program_rejects_entire_update_without_changing_settings(client, program):
    before = client.get("/api/settings").json()["scan"]
    result = client.put("/api/settings/scan", json={
        "interval_minutes": 0, "auto_scan_enabled": False, "program": program,
    })
    assert result.status_code == 400
    assert isinstance(result.json()["detail"], str) and result.json()["detail"]
    assert client.get("/api/settings").json()["scan"] == before


def test_empty_program_allowed_in_interval_mode_but_cannot_activate_it(client):
    result = client.put("/api/settings/scan", json={"interval_minutes": 15, "program": {"times": [], "windows": []}})
    assert result.status_code == 200
    result = client.put("/api/settings/scan", json={"interval_minutes": 0})
    assert result.status_code == 400
    assert client.get("/api/settings").json()["scan"]["interval_minutes"] == 15


def test_program_union_deduplicates_aligned_endpoints_and_rolls_to_next_day():
    program = {"times": ["09:20", "13:30"], "windows": [
        {"start": "09:00", "end": "09:45", "interval_minutes": 20},
        {"start": "09:20", "end": "10:00", "interval_minutes": 20},
    ]}
    now = datetime(2026, 10, 28, 6, 39, tzinfo=UTC)  # Istanbul 09:39
    slots = slots_near(now, 0, program)
    assert slots == sorted(set(slots))
    assert latest_slot(now, 0, program) == datetime(2026, 10, 28, 6, 20, tzinfo=UTC)
    assert next_slot(now, 0, program) == datetime(2026, 10, 28, 6, 40, tzinfo=UTC)
    assert datetime(2026, 10, 28, 6, 45, tzinfo=UTC) not in slots
    assert datetime(2026, 10, 28, 7, tzinfo=UTC) in slots
    assert next_slot(datetime(2026, 10, 28, 10, 30, tzinfo=UTC), 0, program) == datetime(2026, 10, 29, 6, tzinfo=UTC)
    # Positive interval remains independent of the saved program.
    assert next_slot(now, 15, program) == datetime(2026, 10, 28, 6, 45, tzinfo=UTC)


def test_overnight_window_keeps_cadence_across_midnight_and_latest_catchup():
    program = {"times": [], "windows": [{"start": "23:50", "end": "00:25", "interval_minutes": 15}]}
    now = datetime(2026, 10, 28, 21, 7, tzinfo=UTC)  # Istanbul Oct 29 00:07
    assert latest_slot(now, 0, program) == datetime(2026, 10, 28, 21, 5, tzinfo=UTC)
    assert next_slot(now, 0, program) == datetime(2026, 10, 28, 21, 20, tzinfo=UTC)
    assert next_slot(datetime(2026, 10, 28, 21, 20, tzinfo=UTC), 0, program) == datetime(2026, 10, 29, 20, 50, tzinfo=UTC)


def test_scan_status_uses_persisted_program_for_next_run(client, sessions):
    client.put("/api/settings/scan", json={"interval_minutes": 0, "auto_scan_enabled": True,
        "program": {"times": ["13:30"], "windows": []}})
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 28, 10, 29, tzinfo=UTC)
    with sessions() as session, patch("ai_news_radar.scans.datetime", FixedDatetime):
        assert scan_status(session)["next_run_at"] == "2026-10-28T10:30:00+00:00"


def test_scheduler_loop_reload_applies_saved_program_on_next_cycle(client, sessions):
    import ai_news_radar.scheduler as scheduler
    calls = []
    program = {"times": ["13:30"], "windows": []}
    client.put("/api/settings/scan", json={"interval_minutes": 0, "auto_scan_enabled": True, "program": program})
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 28, 10, 45, tzinfo=UTC)
    class StopAfterTwoCycles:
        cycles = 0
        def is_set(self):
            return self.cycles == 2
        def wait(self, seconds):
            self.cycles += 1
            if self.cycles == 1:
                client.put("/api/settings/scan", json={"program": {"times": ["13:40"], "windows": []}})
        def set(self):
            self.cycles = 2
    class InlineWorker:
        def __init__(self, *, target, daemon, kwargs):
            self.target, self.kwargs = target, kwargs
        def start(self):
            self.target(**self.kwargs)
        def is_alive(self):
            return False
        def join(self, timeout):
            pass
    def record_scan(**kwargs):
        calls.append(kwargs["scheduled_for"])
    with patch("ai_news_radar.db.get_session", sessions), patch("ai_news_radar.db.init_db"), \
         patch.object(scheduler, "Event", StopAfterTwoCycles), patch.object(scheduler, "Thread", InlineWorker), \
         patch.object(scheduler, "datetime", FixedDatetime), patch.object(scheduler.signal, "signal"), \
         patch("ai_news_radar.scans.run_scan", record_scan), patch("ai_news_radar.notifications.telegram.publish_pending"):
        scheduler.main()
    assert calls == [datetime(2026, 10, 28, 10, 30, tzinfo=UTC), datetime(2026, 10, 28, 10, 40, tzinfo=UTC)]
