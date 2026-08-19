from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "iPhone 15"}, description="Aranacak ürün, marka veya konu başlığı")
    platform: str = Field(default="reddit", json_schema_extra={"example": "reddit"}, description="Hedef platform")
    limit: int = Field(default=20, ge=1, le=100, description="Çekilecek maksimum yorum sayısı (1-100)")


class CommentItem(BaseModel):
    id: str
    original_text: str
    cleaned_text: str
    label: str
    score: float


class SentimentMetrics(BaseModel):
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    total_comments: int


class Summaries(BaseModel):
    positive_summary: str
    negative_summary: str


class AnalysisResponse(BaseModel):
    query: str
    platform: str
    metrics: SentimentMetrics
    summaries: Summaries
    comments: List[CommentItem]