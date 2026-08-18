from typing import List, Dict, Optional
from app.scrapers.base import BaseScraper
from app.core.logging import logger


class TwitterScraper(BaseScraper):
    """Twitter / X API v2 tabanlı veri çekici (Mock fallback desteği ile)."""

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token
        self.is_configured = bool(bearer_token)
        if not self.is_configured:
            logger.warning("Twitter Bearer Token girilmedi. TwitterScraper mock modunda calisacak.")

    def fetch_comments(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        if not self.is_configured:
            return self._generate_mock_tweets(query, limit)

        # Gerçek Twitter API v2 entegrasyonu (Tweepy veya requests ile)
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&max_results={min(limit, 100)}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json().get("data", [])
                return [{"id": item["id"], "text": item["text"], "platform": "twitter"} for item in data]
            else:
                logger.error(f"Twitter API Hatasi: {response.status_code}")
                return self._generate_mock_tweets(query, limit)
        except Exception as e:
            logger.error(f"Twitter baglanti hatasi: {e}")
            return self._generate_mock_tweets(query, limit)

    def _generate_mock_tweets(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        templates = [
            f"Just bought #{query}! Absolutely loving the design and battery life so far!",
            f"Why is #{query} lagging so much after the update? Really annoying 😡",
            f"Considering whether to buy #{query} or wait for the next generation. Thoughts?",
            f"Great customer support for #{query}, replaced my unit within 2 days!",
            f"Overpriced #{query}. You can find way better alternatives on the market."
        ]
        return [{"id": f"tw_{i + 1}", "text": templates[i % len(templates)], "platform": "twitter_mock"} for i in
                range(limit)]