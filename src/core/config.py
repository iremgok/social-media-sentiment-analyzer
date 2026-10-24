"""
Uygulama konfigürasyonu.

Tüm ayarlar `.env` dosyasından veya ortam değişkenlerinden pydantic-settings
ile okunur ve tip/değer doğrulamasından geçirilir. Uygulamanın geri kalanı
ayarlara yalnızca `get_settings()` üzerinden erişir.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NLPProvider(str, Enum):
    """Duygu analizi ve özetleme için kullanılacak altyapı."""

    AUTO = "auto"                # OpenAI anahtarı varsa OpenAI, yoksa HuggingFace
    HUGGINGFACE = "huggingface"  # Yerel transformer modelleri
    OPENAI = "openai"            # OpenAI Chat Completions API
    LEXICON = "lexicon"          # Model indirmeyen hafif sözlük tabanlı mod (test/demo)


class Settings(BaseSettings):
    """Ortam değişkenlerinden okunan, doğrulanmış uygulama ayarları."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- Genel ---
    PROJECT_NAME: str = "Social Media Sentiment Analyzer"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["*"]

    # --- Veritabanı ---
    DATABASE_URL: str = "sqlite:///./data/sentiment_analyzer.db"

    # --- Twitter / X API v2 ---
    TWITTER_BEARER_TOKEN: Optional[str] = None

    # --- Reddit (PRAW) ---
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "SentimentAnalyzer/2.0"

    # --- NLP ---
    NLP_PROVIDER: NLPProvider = NLPProvider.AUTO
    SENTIMENT_MODEL_NAME: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    SUMMARIZER_MODEL_NAME: str = "sshleifer/distilbart-cnn-12-6"
    ENABLE_ABSTRACTIVE_SUMMARY: bool = True
    SENTIMENT_BATCH_SIZE: int = Field(default=16, ge=1, le=128)

    # --- OpenAI ---
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)

    # --- Scraper ---
    SCRAPER_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)
    MAX_COMMENTS_PER_REQUEST: int = Field(default=100, ge=1, le=500)

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Geçersiz LOG_LEVEL: {value}")
        return value

    @field_validator(
        "TWITTER_BEARER_TOKEN", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "OPENAI_API_KEY",
        mode="before",
    )
    @classmethod
    def _empty_to_none(cls, value: Optional[str]) -> Optional[str]:
        """`.env` içindeki boş anahtarları (KEY=) `None` olarak ele alır."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def resolved_nlp_provider(self) -> NLPProvider:
        """`auto` modunu somut bir sağlayıcıya çözümler."""
        if self.NLP_PROVIDER is not NLPProvider.AUTO:
            return self.NLP_PROVIDER
        return NLPProvider.OPENAI if self.OPENAI_API_KEY else NLPProvider.HUGGINGFACE

    @property
    def twitter_enabled(self) -> bool:
        return bool(self.TWITTER_BEARER_TOKEN)

    @property
    def reddit_enabled(self) -> bool:
        return bool(self.REDDIT_CLIENT_ID and self.REDDIT_CLIENT_SECRET)


@lru_cache
def get_settings() -> Settings:
    """Ayarları tek sefer okuyup önbellekten döndürür."""
    return Settings()
