"""
REST endpoint'leri.

    POST   /analyze          Yeni analiz başlatır ve sonucu kaydeder (201)
    GET    /history          Geçmiş analizlerin sayfalı listesi
    GET    /history/{id}     Tek bir analizin tüm detayları
    DELETE /history/{id}     Analizi siler (204)
    GET    /health           Servis durumu

Route'lar yalnızca HTTP ↔ servis çevirisi yapar; iş mantığı servis katmanındadır.
CPU yoğun NLP işleri event loop'u bloklamasın diye endpoint'ler `def` olarak
tanımlanmıştır (FastAPI bunları thread pool'da çalıştırır).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from src.api.dependencies import ServiceContainer, get_analysis_service, get_container, get_db_service
from src.core.logger import get_logger
from src.models.schemas import AnalysisResult, HealthResponse, HistoryResponse, SentimentRequest
from src.services.analysis_service import AnalysisService, NoCommentsFoundError
from src.services.db_service import DatabaseService

logger = get_logger(__name__)
router = APIRouter()

AnalysisDep = Annotated[AnalysisService, Depends(get_analysis_service)]
DatabaseDep = Annotated[DatabaseService, Depends(get_db_service)]


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    status_code=status.HTTP_201_CREATED,
    tags=["Analysis"],
    summary="Hashtag/anahtar kelime için duygu analizi ve özet üret",
)
def analyze(payload: SentimentRequest, service: AnalysisDep) -> AnalysisResult:
    try:
        return service.run(payload)
    except NoCommentsFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analiz sırasında beklenmeyen hata")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analiz sırasında beklenmeyen bir hata oluştu.",
        ) from exc


@router.get("/history", response_model=HistoryResponse, tags=["History"], summary="Geçmiş analizleri listele")
def list_history(
    db: DatabaseDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[Optional[str], Query(max_length=100, description="Sorgu metnine göre filtre")] = None,
) -> HistoryResponse:
    items, total = db.list_history(limit=limit, offset=offset, query=query)
    return HistoryResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/history/{analysis_id}", response_model=AnalysisResult, tags=["History"], summary="Analiz detayı")
def get_history_item(analysis_id: int, db: DatabaseDep) -> AnalysisResult:
    result = db.get_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analiz bulunamadı.")
    return result


@router.delete(
    "/history/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["History"], summary="Analizi sil"
)
def delete_history_item(analysis_id: int, db: DatabaseDep) -> Response:
    if not db.delete_analysis(analysis_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analiz bulunamadı.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/health", response_model=HealthResponse, tags=["System"], summary="Servis durumu")
def health(container: Annotated[ServiceContainer, Depends(get_container)]) -> HealthResponse:
    db_ok = container.db.ping()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=container.settings.VERSION,
        nlp_provider=container.nlp.provider_name,
        sources=container.scraper.availability(),
        database=db_ok,
    )
