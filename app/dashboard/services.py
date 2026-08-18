import os
import requests
from typing import Dict, Any, Optional

BACKEND_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/analyze/")


class AnalyticsService:
    @staticmethod
    def run_analysis(query: str, platform: str = "reddit", limit: int = 20) -> Optional[Dict[str, Any]]:
        payload = {
            "query": query,
            "platform": platform,
            "limit": limit
        }
        try:
            response = requests.post(BACKEND_URL, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException:
            return None