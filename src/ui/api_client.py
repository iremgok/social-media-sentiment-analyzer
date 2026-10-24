"""
Dashboard'un backend ile konuştuğu HTTP istemcisi.

UI katmanı servis/DB katmanını doğrudan import etmez; tüm veri REST API
üzerinden gelir. Yanıtlar ortak Pydantic şemalarıyla doğrulanır.
"""

import os
from typing import Optional

import requests

from src.models.schemas import AnalysisResult, HealthResponse, HistoryResponse, Platform

DEFAULT_API_URL = "http://localhost:8000/api/v1"


class ApiError(RuntimeError):
    """Backend'e ulaşılamadığında veya hata döndüğünde kullanıcıya gösterilecek mesajı taşır."""


class SentimentApiClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 180.0):
        self._base_url = (base_url or os.getenv("API_URL", DEFAULT_API_URL)).rstrip("/")
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            response = requests.request(method, f"{self._base_url}{path}", timeout=self._timeout, **kwargs)
        except requests.ConnectionError as exc:
            raise ApiError(f"Backend'e bağlanılamadı ({self._base_url}). FastAPI sunucusu çalışıyor mu?") from exc
        except requests.Timeout as exc:
            raise ApiError("Backend zaman aşımına uğradı. Model ilk yüklemede yavaş olabilir, tekrar deneyin.") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiError(f"API hatası ({response.status_code}): {detail}")
        return response

    def health(self) -> HealthResponse:
        return HealthResponse.model_validate(self._request("GET", "/health").json())

    def analyze(self, query: str, platform: Platform, limit: int) -> AnalysisResult:
        payload = {"query": query, "platform": platform.value, "limit": limit}
        return AnalysisResult.model_validate(self._request("POST", "/analyze", json=payload).json())

    def history(self, limit: int = 50, offset: int = 0, query: Optional[str] = None) -> HistoryResponse:
        params = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        return HistoryResponse.model_validate(self._request("GET", "/history", params=params).json())

    def get_analysis(self, analysis_id: int) -> AnalysisResult:
        return AnalysisResult.model_validate(self._request("GET", f"/history/{analysis_id}").json())

    def delete_analysis(self, analysis_id: int) -> None:
        self._request("DELETE", f"/history/{analysis_id}")
