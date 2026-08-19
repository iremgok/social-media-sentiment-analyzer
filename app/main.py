from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.core.config import settings
from app.api.core.logging import logger
from app.api.db.session import engine, Base
from app.api.nlp.preprocessor import TextPreprocessor
from app.api.nlp.sentiment import SentimentAnalyzer
from app.api.nlp.summarizer import TextSummarizer
from app.api.scrapers.reddit_scraper import RedditScraper
from app.api.scrapers.twitter_scraper import TwitterScraper
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting services, initializing ML models...")
    
    # Initialize all ML models and services in app state
    app.state.ml_models = {
        "preprocessor": TextPreprocessor(),
        "sentiment_analyzer": SentimentAnalyzer(model_name=settings.SENTIMENT_MODEL_NAME),
        "summarizer": TextSummarizer(model_name=settings.SUMMARIZER_MODEL_NAME),
        "reddit_scraper": RedditScraper(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        ),
        "twitter_scraper": TwitterScraper(
            bearer_token=settings.TWITTER_BEARER_TOKEN
        )
    }
    
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    logger.info("All services and models loaded successfully!")
    yield
    logger.info("Shutting down and cleaning up models...")
    app.state.ml_models.clear()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Sosyal medya verileri üzerinde duygu analizi ve özetleme yapan NLP boru hattı.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 endpoints
app.include_router(api_router, prefix="/api/v1")


# Root-level health check (for tests and container/orchestration readiness checks)
@app.get("/health", tags=["System"])
async def root_health_check():
    """Sistemin ayakta olup olmadığını kontrol eden uç nokta."""
    ml_models = getattr(app.state, "ml_models", {})
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "models_loaded": bool(ml_models)
    }