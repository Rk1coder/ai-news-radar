from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from ai_news_radar.classification.chat import answer_question
from ai_news_radar.db import get_session, init_db
from ai_news_radar.models import Development, WeeklyDigest
from ai_news_radar.scans import request_scan, scan_status
from ai_news_radar.web.developments_query import query_developments
from ai_news_radar.web.link_preview import fetch_link_preview
from ai_news_radar.web.settings_query import (
    add_custom_source,
    get_settings,
    remove_custom_source,
    set_source_enabled,
    update_scan_settings,
)

app = FastAPI(title="AI News Radar API")
init_db()

SOURCE_TYPE_LABELS = {
    "academic": "Akademik",
    "company": "Şirket",
    "media": "Medya",
    "defense": "Savunma Sanayii",
    "social": "Sosyal Medya",
}


def _serialize(d: Development) -> dict:
    raw = d.raw_item
    return {
        "id": d.id,
        "verified": d.verified,
        "verification_method": d.verification_method,
        "verification_notes": d.verification_notes,
        "technical_impact_score": d.technical_impact_score,
        "hype_score": d.hype_score,
        "applicability_score": d.applicability_score,
        "priority_score": d.priority_score,
        "sector_tags": d.sector_tags or [],
        "classification_rationale": d.classification_rationale,
        "title_tr": d.title_tr,
        "summary_tr": d.summary_tr,
        "raw_item": {
            "title": raw.title,
            "summary": raw.summary,
            "url": raw.url,
            "published_at": raw.published_at.isoformat() if raw.published_at else None,
            "source": {"name": raw.source.name, "source_type": raw.source.source_type},
        },
    }


def _latest_digest(session) -> WeeklyDigest | None:
    return session.query(WeeklyDigest).order_by(WeeklyDigest.generated_at.desc()).first()


def _serialize_digest(digest: WeeklyDigest) -> dict:
    return {
        "content": digest.content,
        "story_count": digest.story_count,
        "generated_at": digest.generated_at.isoformat(),
    }


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class ScanSettingsUpdate(BaseModel):
    interval_minutes: int | None = None
    auto_scan_enabled: bool | None = None


class SourceToggleUpdate(BaseModel):
    enabled: bool


class CustomSourceCreate(BaseModel):
    name: str
    feed_url: str
    source_type: str


def _get_development_or_404(session, dev_id: int) -> Development:
    dev = session.get(Development, dev_id)
    if dev is None:
        raise HTTPException(status_code=404, detail="Gelişme bulunamadı")
    return dev


@app.get("/api/developments/{dev_id}/preview")
def preview(dev_id: int):
    with get_session() as session:
        dev = _get_development_or_404(session, dev_id)
        meta = fetch_link_preview(dev.raw_item.url)
        return {
            "image": meta.get("image"),
            "title": dev.title_tr or dev.raw_item.title,
            "summary": dev.summary_tr or dev.classification_rationale or meta.get("description") or "",
            "url": dev.raw_item.url,
        }


@app.post("/api/developments/{dev_id}/chat")
def chat(dev_id: int, payload: ChatRequest):
    with get_session() as session:
        dev = _get_development_or_404(session, dev_id)
        history = [{"role": m.role, "content": m.content} for m in payload.history]
        answer = answer_question(dev, payload.question, history)
        return {"answer": answer}


@app.post("/api/refresh", status_code=202)
def refresh():
    try:
        result = request_scan(session_factory=get_session)
    except (RuntimeError, TimeoutError):
        raise HTTPException(status_code=503, detail="Tarama başlatılamadı")
    if result is None:
        raise HTTPException(status_code=409, detail="Bir tarama zaten devam ediyor")
    return {"started": True, "scan": result}


@app.get("/api/scan-status")
def get_scan_status():
    with get_session() as session:
        return scan_status(session)


@app.get("/api/settings")
def get_settings_route():
    with get_session() as session:
        return get_settings(session)


@app.put("/api/settings/scan")
def update_scan_settings_route(payload: ScanSettingsUpdate):
    with get_session() as session:
        update_scan_settings(session, **payload.model_dump())
        session.commit()
        return get_settings(session)


@app.put("/api/settings/sources/{source_name}")
def toggle_source_route(source_name: str, payload: SourceToggleUpdate):
    with get_session() as session:
        set_source_enabled(session, source_name, payload.enabled)
        session.commit()
        return get_settings(session)


@app.post("/api/settings/sources/custom", status_code=201)
def add_custom_source_route(payload: CustomSourceCreate):
    with get_session() as session:
        add_custom_source(session, **payload.model_dump())
        session.commit()
        return get_settings(session)


@app.delete("/api/settings/sources/custom/{source_id}")
def remove_custom_source_route(source_id: int):
    with get_session() as session:
        remove_custom_source(session, source_id)
        session.commit()
        return get_settings(session)


@app.get("/api/developments")
def list_developments(
    q: str = Query(default=""),
    sector: str = Query(default=""),
    source_type: str = Query(default=""),
    min_priority: int = Query(default=0),
    show_unverified: bool = Query(default=False),
    sort: str = Query(default=""),
    period: str = Query(default="all", pattern="^(today|week|all)$"),
):
    with get_session() as session:
        result = query_developments(
            session, q=q, sector=sector, source_type=source_type, min_priority=min_priority,
            show_unverified=show_unverified, sort=sort, period=period,
        )
        digest = _latest_digest(session)
        last_fetched_at = result["last_fetched_at"]

        return {
            "weekly_digest": _serialize_digest(digest) if digest else None,
            "scan_status": scan_status(session),
            "developments": [_serialize(d) for d in result["developments"]],
            "search": result["search"],
            "all_sectors": result["all_sectors"],
            "source_type_counts": result["source_type_counts"],
            "source_type_labels": SOURCE_TYPE_LABELS,
            "total_count": result["total_count"],
            "verified_count": result["verified_count"],
            "pending_count": result["pending_count"],
            "last_fetched_at": last_fetched_at.isoformat() if last_fetched_at else None,
        }
