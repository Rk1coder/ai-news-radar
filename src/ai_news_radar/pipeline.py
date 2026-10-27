from collections.abc import Callable

from sqlalchemy.orm import Session

from ai_news_radar.classification.llm_classifier import ClassificationResult, classify
from ai_news_radar.ingestion.base import Connector
from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.notifications.telegram import enqueue as enqueue_telegram
from ai_news_radar.verification.rules import SOURCE_TYPE_DEFAULTS, verify

Notifier = Callable[[Development], None]
# Karar 2/3: pipeline bu adimlarin SONUCUNA bagimli, belirli bir uygulamaya degil -
# verification/rules.verify ve classification/llm_classifier.classify varsayilan,
# ama testler/alternatif stratejiler bunlari degistirebilir (DIP).
VerifyFn = Callable[[RawItem, Source], tuple[bool, str, str]]
ClassifyFn = Callable[[str, str], ClassificationResult]


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
            if exists.published_at is None and fetched.published_at is not None:
                exists.published_at = fetched.published_at
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


def process(
    session: Session, raw_item: RawItem, *, verify_fn: VerifyFn | None = None, classify_fn: ClassifyFn | None = None
) -> Development | None:
    """Karar 2 (dogrulama) + Karar 3 (siniflandirma), tek bir ham kayit icin."""
    verify_fn = verify_fn or verify
    classify_fn = classify_fn or classify
    verified, method, notes = verify_fn(raw_item, raw_item.source)

    development = Development(
        raw_item_id=raw_item.id,
        verified=verified,
        verification_method=method,
        verification_notes=notes,
    )

    if verified:
        result = classify_fn(raw_item.title, raw_item.summary)
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
    session: Session, connectors: list[Connector], notifier: Notifier | None = None,
    on_source_result: Callable[[str, bool], None] | None = None,
    *, verify_fn: VerifyFn | None = None, classify_fn: ClassifyFn | None = None,
) -> list[Development]:
    """Karar 4-A: zamanlanmis, modular batch pipeline - toplama -> dogrulama -> siniflandirma.

    notifier verilirse, dogrulanmis+siniflandirilmis her yeni gelisme icin
    cagrilir (ör. Telegram bildirimi) - cikti kanali pipeline'dan bagimsiz tutulur.
    """
    developments: list[Development] = []
    # Sadece ozellestirilmisse iletilir: process()'i yama (patch) ile degistiren
    # testler eski (session, raw_item) imzasini bekliyor.
    process_kwargs = {}
    if verify_fn is not None:
        process_kwargs["verify_fn"] = verify_fn
    if classify_fn is not None:
        process_kwargs["classify_fn"] = classify_fn
    for connector in connectors:
        source_developments = []
        try:
            for raw_item in ingest(session, connector):
                development = process(session, raw_item, **process_kwargs)
                source_developments.append(development)
                enqueue_telegram(session, development)
            session.commit()
        except Exception as exc:  # noqa: BLE001 - bir kaynagin cokmesi digerlerini durdurmamali
            session.rollback()
            print(f"[{connector.source_name}] basarisiz, atlaniyor: {type(exc).__name__}")
            if on_source_result:
                on_source_result(connector.source_name, False)
            continue
        developments.extend(source_developments)
        if on_source_result:
            on_source_result(connector.source_name, True)
        for development in source_developments:
            if notifier is not None and development.verified:
                notifier(development)
    return developments
