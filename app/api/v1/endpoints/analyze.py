from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, CommentItem, SentimentMetrics, Summaries
from app.nlp.preprocessor import TextPreprocessor
from app.nlp.sentiment import SentimentAnalyzer
from app.nlp.summarizer import TextSummarizer
from app.scrapers.reddit_scraper import RedditScraper
from app.scrapers.twitter_scraper import TwitterScraper
from app.db.session import get_db
from app.db.models import SearchQuery, AnalyzedComment

router = APIRouter()

# Modüller (main.py lifespan icerisinde de singleton tutulabilir)
preprocessor = TextPreprocessor()
sentiment_analyzer = SentimentAnalyzer()
summarizer = TextSummarizer()
reddit_scraper = RedditScraper()
twitter_scraper = TwitterScraper()


@router.post("/", response_model=AnalysisResponse, tags=["Analytics"])
async def analyze_sentiment(payload: AnalysisRequest, db: Session = Depends(get_db)):
    # 1. Platforma göre veriyi çek
    if payload.platform.lower() == "twitter":
        raw_comments = twitter_scraper.fetch_comments(query=payload.query, limit=payload.limit)
    else:
        raw_comments = reddit_scraper.fetch_comments(query=payload.query, limit=payload.limit)

    if not raw_comments:
        raise HTTPException(status_code=404, detail="Analiz edilecek yorum bulunamadi.")

    # 2. Temizle
    cleaned_texts = [preprocessor.clean(c["text"]) for c in raw_comments]

    # 3. Batch Analiz
    sentiment_results = sentiment_analyzer.analyze_batch(cleaned_texts)

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

    # 5. Metrikler ve Özetler
    metrics = sentiment_analyzer.get_summary_metrics(sentiment_results)
    summaries = summarizer.summarize_feedback_by_sentiment(feedbacks_for_summary)

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
    except Exception as db_err:
        db.rollback()

    return AnalysisResponse(
        query=payload.query,
        platform=payload.platform,
        metrics=SentimentMetrics(**metrics),
        summaries=Summaries(**summaries),
        comments=processed_comments
    )