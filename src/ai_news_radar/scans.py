"""Shared coordinator for manual and scheduled scans, with a database-wide lock."""
import fcntl
import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, Lock, Thread

from sqlalchemy import text

from ai_news_radar.classification.digest import generate_weekly_digest
from ai_news_radar.config import AUTO_SCAN_ENABLED, SCAN_HOURS, SCAN_TIMEZONE, SCAN_INTERVAL_MINUTES
from ai_news_radar.db import get_session
from ai_news_radar.ingestion import active_connectors
from ai_news_radar.models import AppSettings, Development, ScanRun, SchedulerHeartbeat, WeeklyDigest
from ai_news_radar.pipeline import run_pipeline
from ai_news_radar.scheduler import next_slot

_memory_lock = Lock()
_SCAN_LOCK = 732891104
HEARTBEAT_STALE_SECONDS = 120
DIGEST_STALE_HOURS = 24


def utc(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def iso(value):
    return utc(value).isoformat() if value else None


@contextmanager
def scan_lock(engine):
    if engine.dialect.name == "postgresql":
        # Dedicated connection: pipeline commits must never release the lock.
        with engine.connect() as connection:
            acquired = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _SCAN_LOCK}).scalar()
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _SCAN_LOCK})
                    connection.commit()
    elif engine.url.database and engine.url.database != ":memory:":
        with open(engine.url.database + ".scan.lock", "a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
            else:
                try:
                    yield True
                finally:
                    fcntl.flock(handle, fcntl.LOCK_UN)
    else:
        acquired = _memory_lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                _memory_lock.release()


def serialize_scan(run):
    return {
        "id": run.id, "status": run.status, "new_count": run.new_count,
        "started_at": iso(run.started_at), "finished_at": iso(run.finished_at),
        "scheduled_for": iso(run.scheduled_for),
        "successful_sources": run.successful_sources,
        "failed_sources": run.failed_sources, "digest_failed": run.digest_failed,
    }


def effective_settings(session):
    """Karar: Ayarlar panelinden kaydedilen deger varsa onu, yoksa config.py varsayilanini kullanir."""
    row = session.get(AppSettings, 1)
    return {
        "interval_minutes": row.scan_interval_minutes if row and row.scan_interval_minutes is not None else SCAN_INTERVAL_MINUTES,
        "auto_scan_enabled": row.auto_scan_enabled if row and row.auto_scan_enabled is not None else AUTO_SCAN_ENABLED,
    }


def scan_status(session):
    now = datetime.now(UTC)
    settings = effective_settings(session)
    latest = session.query(ScanRun).order_by(ScanRun.id.desc()).first()
    successful = session.query(ScanRun).filter(ScanRun.status.in_(["succeeded", "partial"])).order_by(ScanRun.id.desc()).first()
    heartbeat = session.get(SchedulerHeartbeat, 1)
    enabled = settings["auto_scan_enabled"]
    return {
        "enabled": enabled, "hours": SCAN_HOURS, "timezone": SCAN_TIMEZONE,
        "interval_minutes": settings["interval_minutes"],
        "scheduler_online": bool(
            enabled and heartbeat and now - utc(heartbeat.seen_at) < timedelta(seconds=HEARTBEAT_STALE_SECONDS)
        ),
        "next_run_at": iso(next_slot(now, settings["interval_minutes"])) if enabled else None,
        "last_scan": serialize_scan(latest) if latest else None,
        "last_successful_at": iso(successful.finished_at) if successful else None,
    }


def run_scan(session_factory=get_session, connectors=None, *, scheduled_for=None, on_started=None):
    with session_factory() as session:
        with scan_lock(session.get_bind()) as acquired:
            if not acquired:
                return None
            # Having the lock proves any old 'running' row lost its process.
            for old in session.query(ScanRun).filter_by(status="running"):
                old.status = "interrupted"
                old.finished_at = datetime.now(UTC)
            session.commit()
            if scheduled_for is not None:
                existing = session.query(ScanRun).filter(
                    ScanRun.scheduled_for == scheduled_for,
                    ScanRun.status.in_(["succeeded", "partial", "failed"]),
                ).first()
                if existing:
                    return None
            run = ScanRun(scheduled_for=scheduled_for, status="running")
            session.add(run)
            session.commit()
            run_id = run.id
            if on_started:
                on_started(serialize_scan(run))
            failed, successes = [], []
            initial_count = session.query(Development).count()

            def source_finished(name, ok):
                (successes if ok else failed).append(name)
                progress = session.get(ScanRun, run_id)
                progress.successful_sources = len(successes)
                progress.failed_sources = list(failed)
                progress.new_count = session.query(Development).count() - initial_count
                session.commit()

            try:
                developments = run_pipeline(
                    session, active_connectors(session) if connectors is None else connectors,
                    on_source_result=source_finished,
                )
                run = session.get(ScanRun, run_id)
                run.new_count = len(developments)
                run.successful_sources = len(successes)
                run.failed_sources = failed
                final_status = "failed" if not successes else "partial" if failed else "succeeded"
                session.commit()
                latest = session.query(WeeklyDigest).order_by(WeeklyDigest.id.desc()).first()
                stale = latest is None or datetime.now(UTC) - utc(latest.generated_at) > timedelta(hours=DIGEST_STALE_HOURS)
                if successes and (developments or stale) and session.query(Development.id).first():
                    try:
                        content, count = generate_weekly_digest(session)
                        session.add(WeeklyDigest(content=content, story_count=count))
                        session.commit()
                    except Exception:
                        session.rollback()
                        run = session.get(ScanRun, run_id)
                        run.digest_failed = True
                run.status = final_status
                run.finished_at = datetime.now(UTC)
                session.commit()
                return serialize_scan(run)
            except Exception:
                session.rollback()
                run = session.get(ScanRun, run_id)
                run.status = "failed"
                run.finished_at = datetime.now(UTC)
                run.failed_sources = failed
                session.commit()
                raise


def request_scan(session_factory=get_session, connectors=None):
    """Acknowledge only after the worker holds the cross-process lock and saves its run."""
    ready = Event()
    state = {}

    def started(run):
        state['run'] = run
        ready.set()

    def worker():
        try:
            run_scan(session_factory, connectors, on_started=started)
        except Exception as exc:
            state['error'] = True
            logging.getLogger(__name__).warning('Manual scan failed: %s', type(exc).__name__)
        finally:
            ready.set()

    Thread(target=worker, daemon=True, name='manual-news-scan').start()
    if not ready.wait(10):
        raise TimeoutError('Scan start could not be confirmed')
    if state.get('error') and 'run' not in state:
        raise RuntimeError('Scan could not start')
    return state.get('run')
