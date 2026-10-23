from collections.abc import Callable

from sqlalchemy.orm import Session

from ai_news_radar.classification.llm_classifier import classify
from ai_news_radar.ingestion.base import Connector
from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.verification.rules import SOURCE_TYPE_DEFAULTS, verify

Notifier = Callable[[Development], None]


def get_or_create_source(session: Session, connector: Connector) -> Source:
    source = session.query(Source).filter_by(name=connector.source_name).one_or_none()
    if source is not None:
        return source
    defaults = SOURCE_TYPE_DEFAULTS.get(
        connector.source_type, {"credibility_weight": 0.5, "requires_cross_verification": True}
    )
    source = Source(name=connector.source_name, source_type=connector.source_type, **defaults)
    session.add(source)
    session.flush()
    return source


def ingest(session: Session, connector: Connector) -> list[RawItem]:
    """Karar 1-A: connector'i calistirip yeni (henuz gorulmemis) ham kayitlari yazar."""
    source = get_or_create_source(session, connector)
    new_items: list[RawItem] = []
    for fetched in connector.fetch():
        exists = (
            session.query(RawItem)
            .filter_by(source_id=source.id, external_id=fetched.external_id)
            .one_or_none()
        )
        if exists is not None:
            continue
        raw_item = RawItem(
            source_id=source.id,
            external_id=fetched.external_id,
            title=fetched.title,
            url=fetched.url,
            summary=fetched.summary,
            published_at=fetched.published_at,
        )
        session.add(raw_item)
        new_items.append(raw_item)
    session.flush()
    return new_items


def process(session: Session, raw_item: RawItem) -> Development | None:
    """Karar 2 (dogrulama) + Karar 3 (siniflandirma), tek bir ham kayit icin."""
    verified, method, notes = verify(raw_item, raw_item.source)

    development = Development(
        raw_item_id=raw_item.id,
        verified=verified,
        verification_method=method,
        verification_notes=notes,
    )

    if verified:
        result = classify(raw_item.title, raw_item.summary)
        development.technical_impact_score = result.technical_impact_score
        development.hype_score = result.hype_score
        development.applicability_score = result.applicability_score
        development.priority_score = result.priority_score
        development.sector_tags = result.sector_tags
        development.classification_rationale = result.rationale
        development.title_tr = result.title_tr
        development.summary_tr = result.summary_tr

    session.add(development)
    session.flush()
    return development


def run_pipeline(
    session: Session, connectors: list[Connector], notifier: Notifier | None = None
) -> list[Development]:
    """Karar 4-A: zamanlanmis, modular batch pipeline - toplama -> dogrulama -> siniflandirma.

    notifier verilirse, dogrulanmis+siniflandirilmis her yeni gelisme icin
    cagrilir (ör. Telegram bildirimi) - cikti kanali pipeline'dan bagimsiz tutulur.
    """
    developments: list[Development] = []
    for connector in connectors:
        for raw_item in ingest(session, connector):
            development = process(session, raw_item)
            developments.append(development)
            if notifier is not None and development.verified:
                notifier(development)
    session.commit()
    return developments
