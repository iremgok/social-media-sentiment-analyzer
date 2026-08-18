from abc import ABC, abstractmethod
from typing import List, Dict


class BaseScraper(ABC):
    """Tüm sosyal medya scraper sınıfları için standart arayüz."""

    @abstractmethod
    def fetch_comments(self, query: str, limit: int = 50) -> List[Dict[str, str]]:
        """Belirtilen sorguya göre yorumları toplayan ana metot."""
        pass