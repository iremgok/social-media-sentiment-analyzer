"""Twitter / X API v2 "recent search" istemcisi."""

from datetime import datetime
from typing import Optional

import requests

from src.models.schemas import Platform, RawComment
from src.services.scrapers.base import BaseScraper, ScraperError

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
_MIN_PAGE, _MAX_PAGE = 10, 100  # API v2 max_results sınırları


class TwitterScraper(BaseScraper):
    """Bearer token ile son 7 günün tweet'lerini arar (retweet'ler hariç)."""

    platform = Platform.TWITTER

    def __init__(self, bearer_token: Optional[str], timeout: float = 10.0):
        self._token = bearer_token
        self._timeout = timeout

    @property
    def is_available(self) -> bool:
        return bool(self._token)

    @staticmethod
    def build_query(query: str) -> str:
        """Kullanıcı sorgusunu API arama sözdizimine çevirir."""
        return f"{query.strip()} -is:retweet"

    def fetch(self, query: str, limit: int) -> list[RawComment]:
        if not self.is_available:
            raise ScraperError("TWITTER_BEARER_TOKEN tanımlı değil.")

        comments: list[RawComment] = []
        next_token: Optional[str] = None
        while len(comments) < limit:
            page = self._request_page(query, limit - len(comments), next_token)
            comments.extend(self._parse(page))
            next_token = page.get("meta", {}).get("next_token")
            if not next_token:
                break
        return comments[:limit]

    def _request_page(self, query: str, remaining: int, next_token: Optional[str]) -> dict:
        params = {
            "query": self.build_query(query),
            "max_results": max(_MIN_PAGE, min(remaining, _MAX_PAGE)),
            "tweet.fields": "created_at,lang,author_id",
            "expansions": "author_id",
            "user.fields": "username",
        }
        if next_token:
            params["next_token"] = next_token

        try:
            response = requests.get(
                _SEARCH_URL,
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise ScraperError(f"Twitter API'ye ulaşılamadı: {exc}") from exc

        if response.status_code != 200:
            raise ScraperError(f"Twitter API hatası {response.status_code}: {response.text[:200]}")
        return response.json()

    @staticmethod
    def _parse(page: dict) -> list[RawComment]:
        users = {u["id"]: u.get("username") for u in page.get("includes", {}).get("users", [])}
        results = []
        for tweet in page.get("data", []):
            created = tweet.get("created_at")
            results.append(RawComment(
                id=tweet["id"],
                text=tweet["text"],
                platform=Platform.TWITTER,
                author=users.get(tweet.get("author_id")),
                created_at=datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None,
                url=f"https://x.com/i/web/status/{tweet['id']}",
            ))
        return results
