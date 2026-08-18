from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.nlp.preprocessor import TextPreprocessor
from app.nlp.sentiment import SentimentAnalyzer
from app.nlp.summarizer import TextSummarizer
from app.scrapers.reddit_scraper import RedditScraper
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, CommentItem, SentimentMetrics, Summaries

# Global ML modelleri deposu (Bellekte tekil tutulur)
ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sunucu başlarken modelleri yükle (Startup)
    print("Servisler başlatılıyor, yapay zeka modelleri yükleniyor...")
    ml_models["preprocessor"] = TextPreprocessor()
    ml_models["sentiment_analyzer"] = SentimentAnalyzer()
    ml_models["summarizer"] = TextSummarizer()
    ml_models["scraper"] = RedditScraper()
    print("Tüm modeller hazır!")
    yield
    # Sunucu kapanırken temizlik (Shutdown)
    ml_models.clear()


app = FastAPI(
    title="Social Media Sentiment & Summarization API",
    version="1.0.0",
    description="Sosyal medya verileri üzerinde duygu analizi ve özetleme yapan NLP boru hattı.",
    lifespan=lifespan
)

# Frontend ve dashboard erişimleri için CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Sistemin ayakta olup olmadığını kontrol eden uç nokta."""
    return {"status": "healthy", "models_loaded": bool(ml_models)}


@app.post("/api/v1/analyze", response_model=AnalysisResponse, tags=["Analytics"])
async def run_analysis(payload: AnalysisRequest):
    """
    1. Veriyi çeker (Scrape)
    2. Temizler (Preprocess)
    3. Duygu Analizi yapar (RoBERTa)
    4. Özet çıkarır (DistilBART)
    """
    try:
        scraper: RedditScraper = ml_models["scraper"]
        preprocessor: TextPreprocessor = ml_models["preprocessor"]
        sentiment_analyzer: SentimentAnalyzer = ml_models["sentiment_analyzer"]
        summarizer: TextSummarizer = ml_models["summarizer"]

        # 1. Veri Toplama
        raw_comments = scraper.fetch_comments(query=payload.query, limit=payload.limit)
        if not raw_comments:
            raise HTTPException(status_code=404, detail="Yorum bulunamadı.")

        # 2. Ön İşleme
        cleaned_texts = [preprocessor.clean(c["text"]) for c in raw_comments]

        # 3. Duygu Analizi (Toplu / Batch)
        sentiment_results = sentiment_analyzer.analyze_batch(cleaned_texts)

        # 4. Sonuçları birleştir
        processed_comments = []
        feedbacks_for_summary = []

        for raw, cleaned, sent in zip(raw_comments, cleaned_texts, sentiment_results):
            processed_comments.append(CommentItem(
                id=raw["id"],
                original_text=raw["text"],
                cleaned_text=cleaned,
                label=sent["label"],
                score=sent["score"]
            ))
            feedbacks_for_summary.append({"text": cleaned, "label": sent["label"]})

        # 5. Metrikler ve Özetleme
        metrics_dict = sentiment_analyzer.get_summary_metrics(sentiment_results)
        summary_dict = summarizer.summarize_feedback_by_sentiment(feedbacks_for_summary)

        return AnalysisResponse(
            query=payload.query,
            platform=payload.platform,
            metrics=SentimentMetrics(**metrics_dict),
            summaries=Summaries(**summary_dict),
            comments=processed_comments
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz sırasında hata oluştu: {str(e)}")