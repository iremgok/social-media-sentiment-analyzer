"""
FastAPI uygulama giriş noktası.

Çalıştırma:  uvicorn src.main:app --reload
Swagger UI:  http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api.dependencies import ServiceContainer
from src.api.routes import router
from src.core.config import Settings, get_settings
from src.core.logger import configure_logging, get_logger

logger = get_logger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Uygulama fabrikası: testlerde farklı ayarlarla izole uygulama üretmeyi sağlar."""
    settings = settings or get_settings()
    configure_logging(settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Servisler başlatılıyor...")
        app.state.container = ServiceContainer.build(settings)
        logger.info("Uygulama hazır (NLP: %s).", app.state.container.nlp.provider_name)
        yield
        logger.info("Uygulama kapatılıyor.")

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Sosyal medya yorumlarını toplayan, duygu analizi yapan ve özetleyen API.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
