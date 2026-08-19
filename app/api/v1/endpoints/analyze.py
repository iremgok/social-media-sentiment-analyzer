import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.api.schemas.analysis import AnalysisRequest, AnalysisResponse, CommentItem, SentimentMetrics, Summaries
from app.api.nlp.preprocessor import TextPreprocessor
from app.api.nlp.sentiment import SentimentAnalyzer
from app.api.nlp.summarizer import TextSummarizer
from app.api.scrapers.reddit_scraper import RedditScraper
from app.api.scrapers.twitter_scraper import TwitterScraper
from app.api.db.session import get_db
from app.api.db.models import SearchQuery, AnalyzedComment
from app.api.core.logging import logger

router = APIRouter()


# Dependency Injection Helpers
def get_preprocessor(request: Request) -> TextPreprocessor:
    return request.app.state.ml_models["preprocessor"]


def get_sentiment_analyzer(request: Request) -> SentimentAnalyzer:
    return request.app.state.ml_models["sentiment_analyzer"]


def get_summarizer(request: Request) -> TextSummarizer:
    return request.app.state.ml_models["summarizer"]


def get_reddit_scraper(request: Request) -> RedditScraper:
    return request.app.state.ml_models["reddit_scraper"]


def get_twitter_scraper(request: Request) -> TwitterScraper:
    return request.app.state.ml_models["twitter_scraper"]


@router.post("/", response_model=AnalysisResponse, tags=["Analytics"])
async def analyze_sentiment(
    payload: AnalysisRequest,
    db: Session = Depends(get_db),
    preprocessor: TextPreprocessor = Depends(get_preprocessor),
    sentiment_analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
    summarizer: TextSummarizer = Depends(get_summarizer),
    reddit_scraper: RedditScraper = Depends(get_reddit_scraper),
    twitter_scraper: TwitterScraper = Depends(get_twitter_scraper),
):
    logger.info("Received sentiment analysis request for query: '%s' on platform: '%s'", payload.query, payload.platform)

    try:
        # 1. Platforma göre veriyi çek (Scrape)
        if payload.platform.lower() == "twitter":
            logger.info("Scraping Twitter for query '%s' (limit: %d)", payload.query, payload.limit)
            raw_comments = await asyncio.to_thread(
                twitter_scraper.fetch_comments, query=payload.query, limit=payload.limit
            )
        else:
            logger.info("Scraping Reddit for query '%s' (limit: %d)", payload.query, payload.limit)
            raw_comments = await asyncio.to_thread(
                reddit_scraper.fetch_comments, query=payload.query, limit=payload.limit
            )

        if not raw_comments:
            logger.warning("No comments found for query: '%s' on platform: '%s'", payload.query, payload.platform)
            raise HTTPException(status_code=404, detail="Analiz edilecek yorum bulunamadı.")

        logger.info("Successfully scraped %d comments. Commencing preprocessing...", len(raw_comments))

        # 2. Temizle (Preprocess)
        raw_texts = [c["text"] for c in raw_comments]
        cleaned_texts = await asyncio.to_thread(preprocessor.clean_batch, raw_texts)

        logger.info("Preprocessing complete. Running sentiment analysis batch...")

        # 3. Batch Analiz
        sentiment_results = await asyncio.to_thread(sentiment_analyzer.analyze_batch, cleaned_texts)

        logger.info("Sentiment analysis complete. Generating response comments and formatting summary input...")

        # 4. Yorumları Hazırla
        processed_comments = []
        feedbacks_for_summary = []

        for raw, cleaned, sent in zip(raw_comments, cleaned_texts, sentiment_results):
            processed_comments.append(CommentItem(
                id=str(raw["id"]),
                original_text=raw["text"],
                cleaned_text=cleaned,
                label=sent["label"],
                score=sent["score"]
            ))
            feedbacks_for_summary.append({"text": cleaned, "label": sent["label"]})

        logger.info("Generating AI summaries based on sentiment...")

        # 5. Metrikler ve Özetler
        metrics = sentiment_analyzer.get_summary_metrics(sentiment_results)
        summaries = await asyncio.to_thread(summarizer.summarize_feedback_by_sentiment, feedbacks_for_summary)

        logger.info("Saving analysis results to the database...")

        # 6. Veritabanına Kaydet (Log / Cache)
        try:
            search_record = SearchQuery(
                query=payload.query,
                platform=payload.platform,
                total_comments=metrics["total_comments"],
                positive_pct=metrics["positive_pct"],
                negative_pct=metrics["negative_pct"],
                neutral_pct=metrics["neutral_pct"],
                positive_summary=summaries["positive_summary"],
                negative_summary=summaries["negative_summary"]
            )
            db.add(search_record)
            db.flush()

            for c in processed_comments:
                db.add(AnalyzedComment(
                    search_id=search_record.id,
                    external_id=c.id,
                    original_text=c.original_text,
                    cleaned_text=c.cleaned_text,
                    sentiment_label=c.label,
                    sentiment_score=c.score
                ))
            db.commit()
            logger.info("Successfully persisted analysis results in DB (Search ID: %d)", search_record.id)
        except Exception as db_err:
            db.rollback()
            logger.error("Database transaction failed. Rolling back changes. Error: %s", str(db_err))
            # Production environment standard: We log the DB failure but return the output to the user anyway.

        logger.info("Analysis request completed successfully for query: '%s'", payload.query)
        return AnalysisResponse(
            query=payload.query,
            platform=payload.platform,
            metrics=SentimentMetrics(**metrics),
            summaries=Summaries(**summaries),
            comments=processed_comments
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during analysis flow: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analiz sırasında beklenmeyen bir hata oluştu: {str(e)}")