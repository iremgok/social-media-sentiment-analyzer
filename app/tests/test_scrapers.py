from app.api.scrapers.reddit_scraper import RedditScraper
from app.api.scrapers.twitter_scraper import TwitterScraper


def test_reddit_mock_fallback():
    scraper = RedditScraper()  # Key verilmediğinde mock mod
    results = scraper.fetch_comments(query="TestPhone", limit=5)

    assert len(results) == 5
    assert "text" in results[0]
    assert results[0]["platform"] == "reddit_mock"


def test_twitter_mock_fallback():
    scraper = TwitterScraper()
    results = scraper.fetch_comments(query="TestPhone", limit=3)

    assert len(results) == 3
    assert "text" in results[0]