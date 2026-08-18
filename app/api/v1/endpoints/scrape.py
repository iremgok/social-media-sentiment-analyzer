from fastapi import APIRouter, HTTPException
from app.schemas.scraper import ScrapeRequest, RawComment
from app.scrapers.reddit_scraper import RedditScraper
from typing import List

router = APIRouter()
scraper = RedditScraper()


@router.post("/reddit", response_model=List[RawComment], tags=["Scraping"])
async def scrape_reddit(payload: ScrapeRequest):
    data = scraper.fetch_comments(query=payload.query, limit=payload.limit)
    if not data:
        raise HTTPException(status_code=404, detail="Yorum bulunamadi.")
    return data