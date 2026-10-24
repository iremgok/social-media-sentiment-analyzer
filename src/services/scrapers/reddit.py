"""Reddit (PRAW) istemcisi."""

from datetime import datetime, timezone
from typing import Optional

from src.models.schemas import Platform, RawComment
from src.services.scrapers.base import BaseScraper, ScraperError

_MIN_WORDS = 3
_SUBMISSIONS_TO_SCAN = 10


class RedditScraper(BaseScraper):
    """r/all üzerinde arama yapıp en yeni gönderilerin yorumlarını toplar."""

    platform = Platform.REDDIT

    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        user_agent: str,
    ):
        self._credentials = (client_id, client_secret, user_agent)
        self._client = None  # PRAW istemcisi ilk kullanımda oluşturulur

    @property
    def is_available(self) -> bool:
        client_id, client_secret, _ = self._credentials
        return bool(client_id and client_secret)

    def _get_client(self):
        if self._client is None:
            import praw  # Opsiyonel bağımlılık; yalnızca gerektiğinde yüklenir

            client_id, client_secret, user_agent = self._credentials
            self._client = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False,
            )
            self._client.read_only = True
        return self._client

    def fetch(self, query: str, limit: int) -> list[RawComment]:
        if not self.is_available:
            raise ScraperError("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET tanımlı değil.")

        search_term = query.lstrip("#")
        comments: list[RawComment] = []
        try:
            submissions = self._get_client().subreddit("all").search(
                search_term, sort="new", time_filter="week", limit=_SUBMISSIONS_TO_SCAN
            )
            for submission in submissions:
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    if self._is_valid(comment.body):
                        comments.append(self._to_raw(comment))
                    if len(comments) >= limit:
                        return comments
        except Exception as exc:  # PRAW çok çeşitli istisnalar fırlatabilir
            raise ScraperError(f"Reddit verisi çekilemedi: {exc}") from exc
        return comments

    @staticmethod
    def _is_valid(body: Optional[str]) -> bool:
        return bool(body) and body not in ("[deleted]", "[removed]") and len(body.split()) >= _MIN_WORDS

    @staticmethod
    def _to_raw(comment) -> RawComment:
        return RawComment(
            id=comment.id,
            text=comment.body,
            platform=Platform.REDDIT,
            author=str(comment.author) if comment.author else None,
            created_at=datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
            url=f"https://reddit.com{comment.permalink}",
        )
