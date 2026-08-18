from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Media Sentiment Analyzer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Reddit API Credentials
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "SentimentAnalyzer/1.0"

    # Twitter API Credentials (Opsiyonel)
    TWITTER_BEARER_TOKEN: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite:///./sentiment_analyzer.db"

    # NLP Models
    SENTIMENT_MODEL_NAME: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    SUMMARIZER_MODEL_NAME: str = "sshleifer/distilbart-cnn-12-6"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()