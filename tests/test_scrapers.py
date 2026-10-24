"""Veri toplama katmanı testleri (ağ erişimi gerektirmez)."""

from unittest.mock import MagicMock, patch

from src.core.config import Settings
from src.models.schemas import Platform, RawComment
from src.services.scraper_service import ScraperService
from src.services.scrapers import MockScraper, ScraperError, TwitterScraper


def test_mock_scraper_is_deterministic_and_respects_limit():
    first = MockScraper().fetch("#Tesla", 25)
    second = MockScraper().fetch("#Tesla", 25)
    assert len(first) == 25
    assert [c.text for c in first] == [c.text for c in second]
    assert all(c.platform is Platform.MOCK for c in first)
    assert any("Tesla" in c.text for c in first)


def test_mock_scraper_varies_by_query():
    assert [c.text for c in MockScraper().fetch("Tesla", 15)] != [c.text for c in MockScraper().fetch("Xbox", 15)]


def test_service_falls_back_to_mock_without_credentials():
    service = ScraperService.from_settings(Settings(_env_file=None))
    result = service.collect("Tesla", Platform.TWITTER, 10)
    assert result.is_mock_data is True
    assert len(result.comments) == 10


def test_service_falls_back_when_scraper_errors():
    failing = MagicMock(is_available=True)
    failing.fetch.side_effect = ScraperError("429 Too Many Requests")
    service = ScraperService({Platform.TWITTER: failing}, fallback=MockScraper())
    assert service.collect("Tesla", Platform.TWITTER, 5).is_mock_data is True


def test_service_returns_real_data_when_available():
    real = MagicMock(is_available=True)
    real.fetch.return_value = [RawComment(id="1", text="hello world", platform=Platform.REDDIT)]
    service = ScraperService({Platform.REDDIT: real}, fallback=MockScraper())
    result = service.collect("Tesla", Platform.REDDIT, 5)
    assert result.is_mock_data is False and result.comments[0].id == "1"


def test_twitter_scraper_parses_api_response():
    page = {
        "data": [{"id": "42", "text": "Love #Tesla", "author_id": "u1", "created_at": "2026-10-01T12:00:00.000Z"}],
        "includes": {"users": [{"id": "u1", "username": "elon_fan"}]},
        "meta": {},
    }
    response = MagicMock(status_code=200)
    response.json.return_value = page
    with patch("src.services.scrapers.twitter.requests.get", return_value=response) as mock_get:
        comments = TwitterScraper("token").fetch("#Tesla", 10)

    params = mock_get.call_args.kwargs["params"]
    assert params["query"] == "#Tesla -is:retweet"
    assert params["max_results"] == 10
    assert comments[0].author == "elon_fan" and comments[0].created_at.year == 2026
