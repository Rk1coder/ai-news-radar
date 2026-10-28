"""Ayarlar paneli icin is mantigi - app.py'deki route'lar sadece HTTP sekli."""
from fastapi import HTTPException

from ai_news_radar.ingestion import default_connectors
from ai_news_radar.models import AppSettings, CustomSource, ScanProgram, SourceToggle
from ai_news_radar.scan_program import normalize_program
from ai_news_radar.scans import effective_settings

SCAN_INTERVAL_CHOICES = (0, 5, 10, 15, 20, 30, 60)
SOURCE_TYPES = ("academic", "company", "media", "defense", "social")
_UNSET = object()


def get_settings(session) -> dict:
    disabled = {row.source_name for row in session.query(SourceToggle).filter_by(enabled=False)}
    builtin = [
        {"name": c.source_name, "source_type": c.source_type, "enabled": c.source_name not in disabled, "builtin": True}
        for c in default_connectors()
    ]
    custom = [
        {"id": c.id, "name": c.name, "feed_url": c.feed_url, "source_type": c.source_type,
         "enabled": c.enabled, "builtin": False}
        for c in session.query(CustomSource).order_by(CustomSource.created_at)
    ]
    return {"scan": effective_settings(session), "sources": builtin + custom}


def update_scan_settings(session, *, interval_minutes=None, auto_scan_enabled=None, program=_UNSET) -> None:
    if interval_minutes is not None and interval_minutes not in SCAN_INTERVAL_CHOICES:
        raise HTTPException(status_code=400, detail="Gecersiz tarama araligi")
    current = effective_settings(session)
    try:
        selected_program = current["program"] if program is _UNSET else normalize_program(program)
        selected_interval = current["interval_minutes"] if interval_minutes is None else interval_minutes
        if selected_interval == 0 and not (selected_program["times"] or selected_program["windows"]):
            raise ValueError("En az bir tarama saati veya zaman aralığı ekle.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = session.get(AppSettings, 1) or AppSettings(id=1)
    if interval_minutes is not None:
        row.scan_interval_minutes = interval_minutes
    if auto_scan_enabled is not None:
        row.auto_scan_enabled = auto_scan_enabled
    session.merge(row)
    if program is not _UNSET:
        session.merge(ScanProgram(id=1, program=selected_program))


def set_source_enabled(session, source_name: str, enabled: bool) -> None:
    known = {c.source_name for c in default_connectors()}
    if source_name not in known:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadi")
    row = session.query(SourceToggle).filter_by(source_name=source_name).one_or_none()
    if row is None:
        row = SourceToggle(source_name=source_name, enabled=enabled)
        session.add(row)
    else:
        row.enabled = enabled


def add_custom_source(session, *, name: str, feed_url: str, source_type: str) -> CustomSource:
    if source_type not in SOURCE_TYPES:
        raise HTTPException(status_code=400, detail="Gecersiz kaynak turu")
    if not feed_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Gecersiz feed URL'i")
    if session.query(CustomSource).filter_by(name=name).one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Bu isimde bir kaynak zaten var")
    row = CustomSource(name=name, feed_url=feed_url, source_type=source_type)
    session.add(row)
    session.flush()
    return row


def remove_custom_source(session, source_id: int) -> None:
    row = session.get(CustomSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadi")
    session.delete(row)
