"""
API ve servis katmanları arasında taşınan Pydantic şemaları.

Bu modül hiçbir altyapı (DB, HTTP, ML) bağımlılığı içermez; tüm katmanlar
ortak dil olarak bu modelleri kullanır.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Platform(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"
    MOCK = "mock"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# --------------------------------------------------------------------------- #
# Servis içi veri taşıyıcıları
# --------------------------------------------------------------------------- #
class RawComment(BaseModel):
    """Scraper'ların döndürdüğü, işlenmemiş yorum."""

    id: str
    text: str
    platform: Platform
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    url: Optional[str] = None


class SentimentPrediction(BaseModel):
    """Tek bir metin için model çıktısı."""

    label: SentimentLabel
    score: float = Field(ge=0.0, le=1.0)


# --------------------------------------------------------------------------- #
# İstek modelleri
# --------------------------------------------------------------------------- #
class SentimentRequest(BaseModel):
    """`POST /analyze` istek gövdesi."""

    query: str = Field(
        ..., min_length=2, max_length=100,
        description="Aranacak hashtag veya anahtar kelime (örn. #iPhone15 veya 'iPhone 15')",
        examples=["#iPhone15"],
    )
    platform: Platform = Field(default=Platform.TWITTER, description="Veri kaynağı")
    limit: int = Field(default=30, ge=5, le=100, description="Analiz edilecek yorum sayısı")

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        value = value.strip()
        if len(value.lstrip("#")) < 2:
            raise ValueError("Sorgu en az 2 anlamlı karakter içermelidir.")
        return value


# --------------------------------------------------------------------------- #
# Yanıt modelleri
# --------------------------------------------------------------------------- #
class CommentResult(BaseModel):
    """Analiz edilmiş tek bir yorum."""

    model_config = ConfigDict(from_attributes=True)

    external_id: str
    original_text: str
    cleaned_text: str
    language: str = "unknown"
    label: SentimentLabel
    score: float
    author: Optional[str] = None
    created_at: Optional[datetime] = None


class SentimentDistribution(BaseModel):
    """Duygu sınıflarının adet ve yüzde dağılımı."""

    total: int = 0
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0

    @property
    def dominant(self) -> SentimentLabel:
        # Eşitlik durumunda nötr kabul edilir (max ilk en büyüğü döndürür)
        counts = {
            SentimentLabel.NEUTRAL: self.neutral,
            SentimentLabel.POSITIVE: self.positive,
            SentimentLabel.NEGATIVE: self.negative,
        }
        return max(counts, key=counts.get)


class AnalysisSummary(BaseModel):
    """Yapay zeka tarafından üretilen genel görüş özeti."""

    overview: str = Field(description="Kullanıcıların genel görüşünü anlatan 1-2 paragraf")
    positive_highlights: str = ""
    negative_highlights: str = ""


class AnalysisResult(BaseModel):
    """`POST /analyze` ve `GET /history/{id}` yanıtı."""

    id: Optional[int] = None
    query: str
    platform: Platform
    is_mock_data: bool = Field(description="Veri gerçek API yerine mock üreteçten mi geldi?")
    nlp_provider: str
    created_at: datetime
    distribution: SentimentDistribution
    summary: AnalysisSummary
    languages: dict[str, int] = Field(default_factory=dict)
    comments: list[CommentResult]


class HistoryItem(BaseModel):
    """Geçmiş listesindeki özet kayıt."""

    id: int
    query: str
    platform: Platform
    is_mock_data: bool
    nlp_provider: str
    created_at: datetime
    total_comments: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    dominant_sentiment: SentimentLabel


class HistoryResponse(BaseModel):
    """`GET /history` sayfalı yanıtı."""

    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    version: str
    nlp_provider: str
    sources: dict[str, bool]
    database: bool
