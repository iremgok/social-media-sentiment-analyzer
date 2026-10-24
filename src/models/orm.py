"""SQLAlchemy 2.0 ORM tabloları (kalıcılık katmanının veri modeli)."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    """Bir arama/analiz çalıştırmasının özet kaydı."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(100), index=True)
    platform: Mapped[str] = mapped_column(String(20))
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=False)
    nlp_provider: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0)

    overview: Mapped[str] = mapped_column(Text, default="")
    positive_highlights: Mapped[str] = mapped_column(Text, default="")
    negative_highlights: Mapped[str] = mapped_column(Text, default="")

    comments: Mapped[list["CommentRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="CommentRecord.id"
    )


class CommentRecord(Base):
    """Bir analize ait, sınıflandırılmış tek yorum."""

    __tablename__ = "analysis_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="unknown")
    label: Mapped[str] = mapped_column(String(10))
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    analysis: Mapped[AnalysisRecord] = relationship(back_populates="comments")
