"""Ortak test fixture'ları: ağ ve model indirmesi gerektirmeyen izole uygulama."""

import pytest
from fastapi.testclient import TestClient

from src.core.config import NLPProvider, Settings
from src.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,  # Geliştiricinin .env dosyası testleri etkilemesin
        DATABASE_URL=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        NLP_PROVIDER=NLPProvider.LEXICON,
        TWITTER_BEARER_TOKEN=None,
        REDDIT_CLIENT_ID=None,
        REDDIT_CLIENT_SECRET=None,
        OPENAI_API_KEY=None,
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
