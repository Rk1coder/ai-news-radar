from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Query
from sqlalchemy import func

from ai_news_radar.classification.digest import generate_weekly_digest
from ai_news_radar.db import get_session, init_db
from ai_news_radar.ingestion import default_connectors
from ai_news_radar.models import Development, RawItem, Source, WeeklyDigest
from ai_news_radar.pipeline import run_pipeline

DIGEST_MAX_AGE = timedelta(hours=24)

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
            "url": raw.url,
            "published_at": raw.published_at.isoformat() if raw.published_at else None,
            "source": {"name": raw.source.name, "source_type": raw.source.source_type},
        },
    }


def _latest_digest(session) -> WeeklyDigest | None:
    return session.query(WeeklyDigest).order_by(WeeklyDigest.generated_at.desc()).first()


def _get_or_refresh_digest(session, force: bool = False) -> WeeklyDigest:
    existing = _latest_digest(session)
    is_stale = existing is None or (
        datetime.now(UTC) - existing.generated_at.replace(tzinfo=UTC) > DIGEST_MAX_AGE
    )
    if not force and existing is not None and not is_stale:
        return existing

    content, story_count = generate_weekly_digest(session)
    digest = WeeklyDigest(content=content, story_count=story_count)
    session.add(digest)
    session.commit()
    return digest


def _serialize_digest(digest: WeeklyDigest) -> dict:
    return {
        "content": digest.content,
        "story_count": digest.story_count,
        "generated_at": digest.generated_at.isoformat(),
    }


@app.post("/api/refresh")
def refresh():
    session = get_session()
    try:
        developments = run_pipeline(session, default_connectors())
        digest = _get_or_refresh_digest(session, force=True)
    finally:
        session.close()
    return {"refreshed": len(developments), "weekly_digest": _serialize_digest(digest)}


@app.get("/api/developments")
def list_developments(
    q: str = Query(default=""),
    sector: str = Query(default=""),
    source_type: str = Query(default=""),
    min_priority: int = Query(default=0),
    show_unverified: bool = Query(default=False),
    sort: str = Query(default="priority"),
):
    session = get_session()
    try:
        base_query = (
            session.query(Development)
            .join(RawItem, Development.raw_item_id == RawItem.id)
            .join(Source, RawItem.source_id == Source.id)
        )

        total_count = base_query.count()
        verified_count = base_query.filter(Development.verified.is_(True)).count()
        last_fetched_at = session.query(func.max(RawItem.fetched_at)).scalar()

        query = base_query
        if not show_unverified:
            query = query.filter(Development.verified.is_(True))
        if q:
            query = query.filter(RawItem.title.ilike(f"%{q}%"))
        if source_type:
            query = query.filter(Source.source_type == source_type)
        if min_priority:
            query = query.filter(Development.priority_score >= min_priority)

        if sort == "recent":
            query = query.order_by(RawItem.published_at.desc().nullslast())
        else:
            query = query.order_by(Development.priority_score.desc().nullslast())

        developments = query.all()
        if sector:
            developments = [d for d in developments if sector in (d.sector_tags or [])]

        all_sectors = sorted({tag for d in base_query.all() for tag in (d.sector_tags or [])})
        distinct_source_types = [row[0] for row in session.query(Source.source_type).distinct()]
        source_type_counts = {
            st: base_query.filter(Source.source_type == st).count() for st in distinct_source_types
        }

        digest = _get_or_refresh_digest(session)

        return {
            "weekly_digest": _serialize_digest(digest),
            "developments": [_serialize(d) for d in developments],
            "all_sectors": all_sectors,
            "source_type_counts": source_type_counts,
            "source_type_labels": SOURCE_TYPE_LABELS,
            "total_count": total_count,
            "verified_count": verified_count,
            "pending_count": total_count - verified_count,
            "last_fetched_at": last_fetched_at.isoformat() if last_fetched_at else None,
        }
    finally:
        session.close()
