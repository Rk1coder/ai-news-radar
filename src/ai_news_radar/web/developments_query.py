"""Builds the filtered/sorted/searched developments listing - the one place this query logic lives.

Split out of web/app.py so route handlers stay thin HTTP adapters (SRP): this module
knows nothing about HTTP, and app.py knows nothing about SQLAlchemy filtering.
"""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.search import NewsSearch


def query_developments(
    session, *, q="", sector="", source_type="", min_priority=0,
    show_unverified=False, sort="", period="all",
) -> dict:
    base_query = (
        session.query(Development)
        .join(RawItem, Development.raw_item_id == RawItem.id)
        .join(Source, RawItem.source_id == Source.id)
    )

    total_count = base_query.count()
    verified_count = base_query.filter(Development.verified.is_(True)).count()
    last_fetched_at = session.query(func.max(RawItem.fetched_at)).scalar()

    q = q.strip()
    sort = sort or ("relevance" if q else "recent")
    query = base_query.options(joinedload(Development.raw_item).joinedload(RawItem.source))
    if not show_unverified:
        query = query.filter(Development.verified.is_(True))
    if source_type:
        query = query.filter(Source.source_type == source_type)
    if min_priority:
        query = query.filter(Development.priority_score >= min_priority)

    publication = func.coalesce(RawItem.published_at, RawItem.fetched_at)
    if sort == "priority":
        query = query.order_by(
            Development.priority_score.desc().nullslast(), publication.desc(), Development.id.desc()
        )
    else:
        query = query.order_by(publication.desc(), Development.id.desc())
    archive_query = query
    if period != "all":
        local_start = datetime.now(ZoneInfo("Europe/Istanbul")).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = (local_start + timedelta(days=1)).astimezone(UTC).replace(tzinfo=None)
        start = (local_start - timedelta(days=6 if period == "week" else 0)).astimezone(UTC).replace(tzinfo=None)
        query = query.filter(publication >= start, publication < end)

    def in_sector(rows):
        return [d for d in rows if not sector or sector in (d.sector_tags or [])]

    developments = in_sector(query.all())
    search_info = None
    if q:
        search = NewsSearch(q)
        developments = search.filter(developments, relevance=sort == "relevance")
        archive_count = None
        if not developments and period != "all":
            archive_count = len(search.filter(in_sector(archive_query.all())))
        search_info = {"archive_count": archive_count}

    all_sectors = sorted({tag for d in base_query.all() for tag in (d.sector_tags or [])})
    distinct_source_types = [row[0] for row in session.query(Source.source_type).distinct()]
    source_type_counts = {
        st: base_query.filter(Source.source_type == st).count() for st in distinct_source_types
    }

    return {
        "developments": developments,
        "search": search_info,
        "all_sectors": all_sectors,
        "source_type_counts": source_type_counts,
        "total_count": total_count,
        "verified_count": verified_count,
        "pending_count": total_count - verified_count,
        "last_fetched_at": last_fetched_at,
    }
