"""
Veritabanı servisi (Repository pattern).

SQLAlchemy ayrıntılarını üst katmanlardan gizler: dışarıya yalnızca Pydantic
şemaları (`AnalysisResult`, `HistoryItem`) verir ve alır. SQLite ve
PostgreSQL `DATABASE_URL` üzerinden desteklenir.
"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, selectinload, sessionmaker

from src.core.logger import get_logger
from src.models.orm import AnalysisRecord, Base, CommentRecord
from src.models.schemas import (
    AnalysisResult,
    AnalysisSummary,
    CommentResult,
    HistoryItem,
    Platform,
    SentimentDistribution,
)

logger = get_logger(__name__)


def create_db_engine(database_url: str) -> Engine:
    """URL'e göre uygun engine'i oluşturur; SQLite dosyasının klasörünü hazırlar."""
    url = make_url(database_url)
    kwargs: dict = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, **kwargs)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite saat dilimi saklamaz; okunan naive değerleri UTC olarak işaretler."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class DatabaseService:
    """Analiz kayıtlarını saklayan ve sorgulayan repository."""

    def __init__(self, engine: Engine):
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def from_url(cls, database_url: str) -> "DatabaseService":
        return cls(create_db_engine(database_url))

    def init_schema(self) -> None:
        """Tablolar yoksa oluşturur (üretimde Alembic migration'ı tercih edilmelidir)."""
        Base.metadata.create_all(self._engine)
        logger.info("Veritabanı şeması hazır.")

    def ping(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.error("Veritabanı erişilemez: %s", exc)
            return False

    def _session(self) -> Session:
        return self._session_factory()

    # ------------------------------------------------------------------ #
    # Yazma
    # ------------------------------------------------------------------ #
    def save_analysis(self, result: AnalysisResult) -> int:
        """Analizi ve yorumlarını tek transaction'da kaydeder; yeni kaydın id'sini döndürür."""
        dist, summary = result.distribution, result.summary
        record = AnalysisRecord(
            query=result.query,
            platform=result.platform.value,
            is_mock_data=result.is_mock_data,
            nlp_provider=result.nlp_provider,
            created_at=result.created_at,
            total_comments=dist.total,
            positive_count=dist.positive,
            negative_count=dist.negative,
            neutral_count=dist.neutral,
            positive_pct=dist.positive_pct,
            negative_pct=dist.negative_pct,
            neutral_pct=dist.neutral_pct,
            overview=summary.overview,
            positive_highlights=summary.positive_highlights,
            negative_highlights=summary.negative_highlights,
            comments=[
                CommentRecord(
                    external_id=c.external_id,
                    author=c.author,
                    original_text=c.original_text,
                    cleaned_text=c.cleaned_text,
                    language=c.language,
                    label=c.label.value,
                    score=c.score,
                    created_at=c.created_at,
                )
                for c in result.comments
            ],
        )
        with self._session() as session, session.begin():
            session.add(record)
        logger.info("Analiz kaydedildi (id=%d, sorgu='%s').", record.id, record.query)
        return record.id

    def delete_analysis(self, analysis_id: int) -> bool:
        with self._session() as session, session.begin():
            record = session.get(AnalysisRecord, analysis_id)
            if record is None:
                return False
            session.delete(record)
        return True

    # ------------------------------------------------------------------ #
    # Okuma
    # ------------------------------------------------------------------ #
    def list_history(
        self, limit: int = 20, offset: int = 0, query: Optional[str] = None
    ) -> tuple[list[HistoryItem], int]:
        """En yeniden eskiye sayfalı geçmiş listesi ve toplam kayıt sayısını döndürür."""
        filters = [AnalysisRecord.query.ilike(f"%{query.strip()}%")] if query and query.strip() else []
        with self._session() as session:
            total = session.scalar(select(func.count(AnalysisRecord.id)).where(*filters)) or 0
            records = session.scalars(
                select(AnalysisRecord)
                .where(*filters)
                .order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._to_history_item(r) for r in records], total

    def get_analysis(self, analysis_id: int) -> Optional[AnalysisResult]:
        with self._session() as session:
            record = session.scalar(
                select(AnalysisRecord)
                .options(selectinload(AnalysisRecord.comments))
                .where(AnalysisRecord.id == analysis_id)
            )
            return self._to_result(record) if record else None

    # ------------------------------------------------------------------ #
    # ORM -> Şema dönüşümleri
    # ------------------------------------------------------------------ #
    @staticmethod
    def _distribution(record: AnalysisRecord) -> SentimentDistribution:
        return SentimentDistribution(
            total=record.total_comments,
            positive=record.positive_count,
            negative=record.negative_count,
            neutral=record.neutral_count,
            positive_pct=record.positive_pct,
            negative_pct=record.negative_pct,
            neutral_pct=record.neutral_pct,
        )

    @classmethod
    def _to_history_item(cls, record: AnalysisRecord) -> HistoryItem:
        return HistoryItem(
            id=record.id,
            query=record.query,
            platform=Platform(record.platform),
            is_mock_data=record.is_mock_data,
            nlp_provider=record.nlp_provider,
            created_at=_as_utc(record.created_at),
            total_comments=record.total_comments,
            positive_pct=record.positive_pct,
            negative_pct=record.negative_pct,
            neutral_pct=record.neutral_pct,
            dominant_sentiment=cls._distribution(record).dominant,
        )

    @classmethod
    def _to_result(cls, record: AnalysisRecord) -> AnalysisResult:
        comments = [
            CommentResult(
                external_id=c.external_id,
                original_text=c.original_text,
                cleaned_text=c.cleaned_text,
                language=c.language,
                label=c.label,
                score=c.score,
                author=c.author,
                created_at=_as_utc(c.created_at),
            )
            for c in record.comments
        ]
        return AnalysisResult(
            id=record.id,
            query=record.query,
            platform=Platform(record.platform),
            is_mock_data=record.is_mock_data,
            nlp_provider=record.nlp_provider,
            created_at=_as_utc(record.created_at),
            distribution=cls._distribution(record),
            summary=AnalysisSummary(
                overview=record.overview,
                positive_highlights=record.positive_highlights,
                negative_highlights=record.negative_highlights,
            ),
            languages=dict(Counter(c.language for c in comments).most_common()),
            comments=comments,
        )
