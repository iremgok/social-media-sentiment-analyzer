"""
Bağımlılık enjeksiyonu (Dependency Injection).

Servisler uygulama açılışında bir kez oluşturulup `app.state.container`
içinde tutulur; route'lar onlara yalnızca bu fonksiyonlar üzerinden erişir.
Testlerde `app.dependency_overrides` ile kolayca değiştirilebilirler.
"""

from dataclasses import dataclass

from fastapi import Request

from src.core.config import Settings
from src.services.analysis_service import AnalysisService
from src.services.db_service import DatabaseService
from src.services.nlp_service import NLPService
from src.services.scraper_service import ScraperService


@dataclass
class ServiceContainer:
    settings: Settings
    db: DatabaseService
    scraper: ScraperService
    nlp: NLPService
    analysis: AnalysisService

    @classmethod
    def build(cls, settings: Settings) -> "ServiceContainer":
        db = DatabaseService.from_url(settings.DATABASE_URL)
        db.init_schema()
        scraper = ScraperService.from_settings(settings)
        nlp = NLPService.from_settings(settings)
        return cls(settings, db, scraper, nlp, AnalysisService(scraper, nlp, db))


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


def get_analysis_service(request: Request) -> AnalysisService:
    return get_container(request).analysis


def get_db_service(request: Request) -> DatabaseService:
    return get_container(request).db
