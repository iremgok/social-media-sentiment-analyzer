"""OpenAI Chat Completions tabanlı duygu analizi ve özetleme stratejileri."""

import json

from src.core.logger import get_logger
from src.models.schemas import (
    AnalysisSummary,
    CommentResult,
    SentimentDistribution,
    SentimentLabel,
    SentimentPrediction,
)
from src.services.nlp.sentiment import SentimentAnalyzer, normalize_label
from src.services.nlp.summarizer import Summarizer

logger = get_logger(__name__)

_CHUNK_SIZE = 25          # Tek istekte sınıflandırılacak yorum sayısı
_MAX_SUMMARY_SAMPLES = 40
_MAX_COMMENT_CHARS = 280

_SENTIMENT_PROMPT = (
    "You are a sentiment classifier for social media comments in any language. "
    "Classify each numbered comment as positive, negative or neutral and give a confidence "
    "between 0 and 1. Respond ONLY with JSON: "
    '{"results": [{"i": <number>, "label": "positive|negative|neutral", "score": <float>}]}'
)

_SUMMARY_PROMPT = (
    "Sen bir sosyal medya analistisin. Sana bir konu, duygu dağılımı ve örnek yorumlar verilecek. "
    "Türkçe olarak SADECE şu JSON'u döndür: "
    '{"overview": "...", "positive_highlights": "...", "negative_highlights": "..."}. '
    "'overview' kullanıcıların genel görüşünü anlatan 1-2 paragraf olsun (paragrafları \\n\\n ile ayır). "
    "'positive_highlights' ve 'negative_highlights' öne çıkan övgü ve şikayetleri 2-3 cümlede özetlesin. "
    "Yorumlarda olmayan bilgi uydurma."
)


class _OpenAIClient:
    """OpenAI SDK'sını saran ince katman; JSON yanıtı ayrıştırır."""

    def __init__(self, api_key: str, model: str, timeout: float):
        from openai import OpenAI  # Opsiyonel bağımlılık

        self._client = OpenAI(api_key=api_key, timeout=timeout, max_retries=2)
        self._model = model

    def complete_json(self, system: str, user: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return json.loads(response.choices[0].message.content or "{}")


class OpenAISentimentAnalyzer(SentimentAnalyzer):
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float = 30.0):
        self._client = _OpenAIClient(api_key, model, timeout)

    def predict(self, texts: list[str]) -> list[SentimentPrediction]:
        results: list[SentimentPrediction] = []
        for start in range(0, len(texts), _CHUNK_SIZE):
            results.extend(self._predict_chunk(texts[start: start + _CHUNK_SIZE]))
        return results

    def _predict_chunk(self, chunk: list[str]) -> list[SentimentPrediction]:
        numbered = "\n".join(f"{i}. {text[:_MAX_COMMENT_CHARS]}" for i, text in enumerate(chunk))
        payload = self._client.complete_json(_SENTIMENT_PROMPT, numbered)

        predictions = [SentimentPrediction(label=SentimentLabel.NEUTRAL, score=0.5)] * len(chunk)
        for item in payload.get("results", []):
            index = item.get("i")
            if isinstance(index, int) and 0 <= index < len(chunk):
                score = min(max(float(item.get("score", 0.5)), 0.0), 1.0)
                predictions[index] = SentimentPrediction(
                    label=normalize_label(str(item.get("label", "neutral"))), score=round(score, 4)
                )
        return predictions


class OpenAISummarizer(Summarizer):
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float = 30.0):
        self._client = _OpenAIClient(api_key, model, timeout)

    def summarize(
        self, query: str, distribution: SentimentDistribution, comments: list[CommentResult]
    ) -> AnalysisSummary:
        samples = sorted(comments, key=lambda c: c.score, reverse=True)[:_MAX_SUMMARY_SAMPLES]
        lines = "\n".join(f"[{c.label.value}] {c.cleaned_text[:_MAX_COMMENT_CHARS]}" for c in samples)
        user_message = (
            f"Konu: {query}\n"
            f"Dağılım: %{distribution.positive_pct} olumlu, %{distribution.negative_pct} olumsuz, "
            f"%{distribution.neutral_pct} nötr (toplam {distribution.total} yorum)\n\nYorumlar:\n{lines}"
        )
        payload = self._client.complete_json(_SUMMARY_PROMPT, user_message)
        if not payload.get("overview"):
            raise ValueError("OpenAI yanıtında 'overview' alanı yok.")
        return AnalysisSummary(
            overview=str(payload["overview"]).strip(),
            positive_highlights=str(payload.get("positive_highlights", "")).strip(),
            negative_highlights=str(payload.get("negative_highlights", "")).strip(),
        )
