from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Bir ingestion connector'inin beslediği mantiksal kaynak (Karar 1)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    source_type: Mapped[str] = mapped_column(String(50))  # academic | company | defense | social
    # Karar 2: kaynak turune gore degisen dogrulama esigi
    credibility_weight: Mapped[float] = mapped_column(Float, default=0.5)
    requires_cross_verification: Mapped[bool] = mapped_column(Boolean, default=True)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")


class RawItem(Base):
    """Bir connector'in tek bir calismada cektigi ham icerik."""

    __tablename__ = "raw_items"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(500))  # kaynaktaki orijinal id/url
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    source: Mapped["Source"] = relationship(back_populates="raw_items")
    development: Mapped["Development | None"] = relationship(
        back_populates="raw_item", uselist=False
    )


class Development(Base):
    """Dogrulama + siniflandirma sonrasi uretilen, kullaniciya sunulan gelisme kaydi (Karar 2/3)."""

    __tablename__ = "developments"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_item_id: Mapped[int] = mapped_column(ForeignKey("raw_items.id"), unique=True)

    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_method: Mapped[str] = mapped_column(String(50), default="")  # rule | llm | hybrid
    verification_notes: Mapped[str] = mapped_column(Text, default="")

    # Karar 3: uc ayri skor, 0-100 arasi
    technical_impact_score: Mapped[int | None] = mapped_column(nullable=True)
    hype_score: Mapped[int | None] = mapped_column(nullable=True)
    applicability_score: Mapped[int | None] = mapped_column(nullable=True)
    priority_score: Mapped[int | None] = mapped_column(nullable=True)

    sector_tags: Mapped[list] = mapped_column(JSON, default=list)  # ornek: ["defense", "healthcare"]
    classification_rationale: Mapped[str] = mapped_column(Text, default="")

    # Karar 3: siniflandirma sirasinda uretilen Turkce ceviri; bos ise arayuz orijinali gosterir.
    title_tr: Mapped[str] = mapped_column(Text, default="")
    summary_tr: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    raw_item: Mapped["RawItem"] = relationship(back_populates="development")
