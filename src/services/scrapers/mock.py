"""
Akıllı mock veri üreteci.

API anahtarı yokken veya gerçek kaynak hata verdiğinde devreye girer.
Özellikleri:
  * Aynı sorgu için deterministik (tekrarlanabilir) sonuç üretir,
  * Sorguya göre farklı duygu dağılımları oluşturur,
  * Türkçe ve İngilizce yorumları karıştırır,
  * Ön işleme adımını sınamak için URL, @mention, #hashtag ve emoji ekler.
"""

import hashlib
import random
from datetime import datetime, timedelta, timezone

from src.models.schemas import Platform, RawComment
from src.services.scrapers.base import BaseScraper

_TEMPLATES: dict[str, list[str]] = {
    "positive": [
        "I've been using {q} for a week and honestly it's amazing. Battery life is fantastic!",
        "{q} exceeded all my expectations, best purchase I made this year.",
        "The design of {q} is gorgeous and it feels super fast. Highly recommend it!",
        "Customer support for {q} was excellent, they solved my issue in minutes.",
        "{q} için gerçekten harika diyebilirim, performansı mükemmel!",
        "{q} aldım ve çok memnunum, kesinlikle tavsiye ederim.",
        "Fiyatına göre {q} süper bir seçim, kalitesi çok iyi.",
    ],
    "negative": [
        "Totally disappointed with {q}. The latest update made it slow and buggy.",
        "{q} is way overpriced for what it offers. Terrible value.",
        "Overheating issues on {q} are awful, I want a refund.",
        "Worst customer service ever, {q} broke after two days.",
        "{q} tam bir hayal kırıklığı, sürekli donuyor ve çöküyor.",
        "{q} için verdiğim paraya yazık, kalitesi çok kötü.",
        "Kargo berbattı, {q} kutusu hasarlı geldi. Hiç memnun değilim.",
    ],
    "neutral": [
        "Has anyone tried {q} yet? Thinking about buying one.",
        "{q} arrived today. Will share my thoughts after testing it.",
        "Comparing {q} with the previous version, the specs look similar.",
        "{q} hakkında yorumlarınızı merak ediyorum, almaya değer mi?",
        "{q} bugün elime ulaştı, birkaç gün kullanıp yazacağım.",
        "Is {q} available in other colors? Just asking.",
    ],
}

_DECORATIONS = {
    "positive": [" 😍", " 🔥🔥", " 👍", ""],
    "negative": [" 😡", " 👎", " 🤦", ""],
    "neutral": [" 🤔", " 👀", ""],
}
_EXTRAS = ["", "", " https://example.com/review", " @techreviewer", " #tech"]
_AUTHORS = ["ayse_k", "mehmet.dev", "techfan", "jane_doe", "gamer42", "zeynep_t", "alex_r", "can.b"]


class MockScraper(BaseScraper):
    """Gerçekçi, deterministik sentetik sosyal medya yorumları üretir."""

    platform = Platform.MOCK

    @property
    def is_available(self) -> bool:
        return True

    def fetch(self, query: str, limit: int) -> list[RawComment]:
        rng = random.Random(self._seed(query))
        topic = query.strip()
        hashtag = "#" + topic.lstrip("#").replace(" ", "")
        weights = self._sentiment_weights(rng)
        now = datetime.now(timezone.utc)

        comments = []
        for index in range(limit):
            sentiment = rng.choices(list(weights), weights=list(weights.values()))[0]
            mention = rng.choice([topic.lstrip("#"), hashtag])
            text = rng.choice(_TEMPLATES[sentiment]).format(q=mention)
            text += rng.choice(_DECORATIONS[sentiment]) + rng.choice(_EXTRAS)
            comments.append(RawComment(
                id=f"mock_{index + 1}",
                text=text,
                platform=Platform.MOCK,
                author=rng.choice(_AUTHORS),
                created_at=now - timedelta(minutes=rng.randint(1, 60 * 72)),
            ))
        comments.sort(key=lambda c: c.created_at, reverse=True)
        return comments

    @staticmethod
    def _seed(query: str) -> int:
        """Python'un `hash()`'inden farklı olarak süreçler arası kararlı tohum üretir."""
        return int(hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:8], 16)

    @staticmethod
    def _sentiment_weights(rng: random.Random) -> dict[str, float]:
        """Her sorgu için farklı ama makul bir duygu karışımı oluşturur."""
        positive = rng.uniform(0.2, 0.6)
        negative = rng.uniform(0.15, 0.8 - positive)
        return {"positive": positive, "negative": negative, "neutral": 1.0 - positive - negative}
