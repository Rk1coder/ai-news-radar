"""Interval or daily scans, independent of browsers/API workers."""
import logging
import signal
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from zoneinfo import ZoneInfo

from ai_news_radar.config import AUTO_SCAN_ENABLED, SCAN_HOURS, SCAN_TIMEZONE, SCAN_INTERVAL_MINUTES
from ai_news_radar.scan_program import program_minutes

log = logging.getLogger(__name__)


def slots_near(now: datetime, interval_minutes: int | None = None, program: dict | None = None) -> list[datetime]:
    if interval_minutes is None:
        interval_minutes = SCAN_INTERVAL_MINUTES
    local = now.astimezone(ZoneInfo(SCAN_TIMEZONE))
    if interval_minutes:
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return sorted(
            (midnight + timedelta(days=day, minutes=minute)).astimezone(UTC)
            for day in (-1, 0, 1) for minute in range(0, 1440, interval_minutes)
        )
    if program is not None:
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return sorted({
            (midnight + timedelta(days=day, minutes=minute)).astimezone(UTC)
            for day in (-1, 0, 1) for minute in program_minutes(program)
        })
    return sorted(
        (local + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0).astimezone(UTC)
        for day in (-1, 0, 1) for hour in SCAN_HOURS
    )


def latest_slot(now: datetime, interval_minutes: int | None = None, program: dict | None = None) -> datetime:
    return max(slot for slot in slots_near(now, interval_minutes, program) if slot <= now)


def next_slot(now: datetime, interval_minutes: int | None = None, program: dict | None = None) -> datetime:
    return min(slot for slot in slots_near(now, interval_minutes, program) if slot > now)


def run_cycle(*, auto_scan_enabled: bool | None = None, interval_minutes: int | None = None, program: dict | None = None):
    from ai_news_radar.scans import run_scan
    from ai_news_radar.notifications.telegram import publish_pending

    if auto_scan_enabled is None:
        auto_scan_enabled = AUTO_SCAN_ENABLED
    if auto_scan_enabled:
        try:
            result = run_scan(scheduled_for=latest_slot(datetime.now(UTC), interval_minutes, program))
            if result:
                log.info("Scan %s: %s, %s new", result["id"], result["status"], result["new_count"])
        except Exception as exc:
            log.warning("Scheduled scan failed: %s", type(exc).__name__)
    try:
        publish_pending()
    except Exception as exc:
        log.warning("Telegram queue could not be processed: %s", type(exc).__name__)


def main() -> None:
    from ai_news_radar.db import get_session, init_db
    from ai_news_radar.models import SchedulerHeartbeat
    from ai_news_radar.scans import effective_settings

    logging.basicConfig(level=logging.INFO)
    init_db()
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    worker = None
    while not stop.is_set():
        settings = {"auto_scan_enabled": AUTO_SCAN_ENABLED, "interval_minutes": SCAN_INTERVAL_MINUTES}
        try:
            with get_session() as session:
                settings = effective_settings(session)
                if settings["auto_scan_enabled"]:
                    session.merge(SchedulerHeartbeat(id=1, seen_at=datetime.now(UTC)))
                    session.commit()
        except Exception as exc:
            log.warning("Scheduler heartbeat failed: %s", type(exc).__name__)
        if worker is None or not worker.is_alive():
            worker = Thread(
                target=run_cycle, daemon=True,
                kwargs={"auto_scan_enabled": settings["auto_scan_enabled"],
                        "interval_minutes": settings["interval_minutes"], "program": settings.get("program")},
            )
            worker.start()
        stop.wait(30)
    if worker:
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
