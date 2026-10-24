"""
Analiz kullanım senaryosu (use case).

Veri toplama, NLP ve kalıcılık servislerini tek bir iş akışında birleştirir.
API katmanı yalnızca bu sınıfı çağırır; böylece route'lar ince kalır ve aynı
akış CLI, zamanlanmış görev vb. farklı arayüzlerden de tetiklenebilir.
"""

from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.schemas import AnalysisResult, SentimentRequest
from src.services.db_service import DatabaseService
from src.services.nlp_service import NLPService
from src.services.scraper_service import ScraperService

logger = get_logger(__name__)


class NoCommentsFoundError(LookupError):
    """Hiçbir kaynaktan analiz edilecek yorum gelmediğinde fırlatılır."""


class AnalysisService:
    def __init__(self, scraper: ScraperService, nlp: NLPService, db: DatabaseService):
        self._scraper = scraper
        self._nlp = nlp
        self._db = db

    def run(self, request: SentimentRequest) -> AnalysisResult:
        logger.info("Analiz başladı: sorgu='%s', platform=%s, limit=%d",
                    request.query, request.platform.value, request.limit)

        scraped = self._scraper.collect(request.query, request.platform, request.limit)
        if not scraped.comments:
            raise NoCommentsFoundError(f"'{request.query}' için yorum bulunamadı.")

        nlp = self._nlp.analyze(request.query, scraped.comments)
        result = AnalysisResult(
            query=request.query,
            platform=request.platform,
            is_mock_data=scraped.is_mock_data,
            nlp_provider=nlp.provider,
            created_at=datetime.now(timezone.utc),
            distribution=nlp.distribution,
            summary=nlp.summary,
            languages=nlp.languages,
            comments=nlp.comments,
        )

        try:
            result.id = self._db.save_analysis(result)
        except Exception as exc:
            # Kalıcılık hatası kullanıcıya sonucu göstermeye engel olmamalı
            logger.error("Analiz veritabanına kaydedilemedi: %s", exc, exc_info=True)

        logger.info("Analiz tamamlandı: %d yorum, baskın duygu=%s",
                    result.distribution.total, result.distribution.dominant.value)
        return result
