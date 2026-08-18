from fastapi import APIRouter
from app.api.v1.endpoints import health, scrape, analyze

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["System"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["Scraping"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Analytics"])