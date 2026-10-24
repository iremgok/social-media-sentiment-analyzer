"""Tüm veri kaynakları için ortak arayüz."""

from abc import ABC, abstractmethod

from src.models.schemas import Platform, RawComment


class ScraperError(RuntimeError):
    """Bir veri kaynağından veri çekilemediğinde fırlatılır."""


class BaseScraper(ABC):
    """Sosyal medya veri kaynağı sözleşmesi (Strategy pattern)."""

    platform: Platform

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Kaynak kullanıma hazır mı (ör. API anahtarı tanımlı mı)?"""

    @abstractmethod
    def fetch(self, query: str, limit: int) -> list[RawComment]:
        """Sorguya uyan en güncel `limit` adet yorumu döndürür.

        Raises:
            ScraperError: Kaynağa ulaşılamadığında veya yanıt geçersiz olduğunda.
        """
