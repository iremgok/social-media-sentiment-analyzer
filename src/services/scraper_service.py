"""
Veri toplama servisi.

Platform seçimine göre doğru scraper'ı çalıştırır; kaynak yapılandırılmamışsa,
hata verirse veya boş dönerse otomatik olarak mock üretece düşer (graceful
degradation). Üst katmanlar hangi scraper'ın çalıştığını bilmek zorunda değildir.
"""

from dataclasses import dataclass

from src.core.config import Settings
from src.core.logger import get_logger
from src.models.schemas import Platform, RawComment
from src.services.scrapers import BaseScraper, MockScraper, RedditScraper, ScraperError, TwitterScraper

logger = get_logger(__name__)


@dataclass(frozen=True)
class ScrapeResult:
    comments: list[RawComment]
    is_mock_data: bool


class ScraperService:
    """Scraper stratejilerini yöneten cephe (facade)."""

    def __init__(self, scrapers: dict[Platform, BaseScraper], fallback: BaseScraper):
        self._scrapers = scrapers
        self._fallback = fallback

    @classmethod
    def from_settings(cls, settings: Settings) -> "ScraperService":
        return cls(
            scrapers={
                Platform.TWITTER: TwitterScraper(
                    settings.TWITTER_BEARER_TOKEN, timeout=settings.SCRAPER_TIMEOUT_SECONDS
                ),
                Platform.REDDIT: RedditScraper(
                    settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET, settings.REDDIT_USER_AGENT
                ),
            },
            fallback=MockScraper(),
        )

    def availability(self) -> dict[str, bool]:
        """Her platformun gerçek API ile çalışıp çalışmadığını raporlar."""
        status = {p.value: s.is_available for p, s in self._scrapers.items()}
        status[Platform.MOCK.value] = True
        return status

    def collect(self, query: str, platform: Platform, limit: int) -> ScrapeResult:
        """Yorumları toplar; gerekirse mock veriye düşer."""
        scraper = self._scrapers.get(platform)

        if scraper is None or not scraper.is_available:
            if platform is not Platform.MOCK:
                logger.warning("'%s' için API anahtarı yok, mock veri kullanılıyor.", platform.value)
            return self._from_fallback(query, limit)

        try:
            comments = scraper.fetch(query, limit)
        except ScraperError as exc:
            logger.error("'%s' kaynağı hata verdi (%s); mock veriye geçiliyor.", platform.value, exc)
            return self._from_fallback(query, limit)

        if not comments:
            logger.warning("'%s' için '%s' sorgusunda sonuç yok; mock veriye geçiliyor.", platform.value, query)
            return self._from_fallback(query, limit)

        logger.info("%s kaynağından %d yorum toplandı.", platform.value, len(comments))
        return ScrapeResult(comments=comments, is_mock_data=False)

    def _from_fallback(self, query: str, limit: int) -> ScrapeResult:
        return ScrapeResult(comments=self._fallback.fetch(query, limit), is_mock_data=True)
