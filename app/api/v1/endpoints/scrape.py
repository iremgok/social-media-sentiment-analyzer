from fastapi import APIRouter, HTTPException, Depends, Request
from app.api.schemas.scraper import ScrapeRequest, RawComment
from app.api.scrapers.reddit_scraper import RedditScraper
from typing import List
import asyncio

router = APIRouter()


def get_reddit_scraper(request: Request) -> RedditScraper:
    return request.app.state.ml_models["reddit_scraper"]


@router.post("/reddit", response_model=List[RawComment], tags=["Scraping"])
async def scrape_reddit(payload: ScrapeRequest, scraper: RedditScraper = Depends(get_reddit_scraper)):
    try:
        data = await asyncio.to_thread(scraper.fetch_comments, query=payload.query, limit=payload.limit)
        if not data:
            raise HTTPException(status_code=404, detail="Yorum bulunamadi.")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri çekme sırasında hata oluştu: {str(e)}")