"""
Duygu sınıflandırma stratejileri.

  * `LexiconSentimentAnalyzer`     – bağımlılıksız, anında çalışan yedek analizci
  * `HuggingFaceSentimentAnalyzer` – transformers pipeline'ı ile yerel model

OpenAI tabanlı analizci `openai_backend.py` içindedir. Hepsi aynı
`SentimentAnalyzer` sözleşmesini uygular.
"""

import re
from abc import ABC, abstractmethod

from src.core.logger import get_logger
from src.models.schemas import SentimentLabel, SentimentPrediction
from src.services.nlp.lexicon import NEGATIVE_WORDS, NEGATORS_AFTER, NEGATORS_BEFORE, POSITIVE_WORDS

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_EMPTY_PREDICTION = SentimentPrediction(label=SentimentLabel.NEUTRAL, score=0.5)


class SentimentAnalyzer(ABC):
    """Metin listesini duygu tahminlerine çeviren strateji arayüzü."""

    name: str

    @abstractmethod
    def predict(self, texts: list[str]) -> list[SentimentPrediction]:
        """Girdi ile aynı uzunlukta ve sırada tahmin listesi döndürür."""


def normalize_label(raw_label: str) -> SentimentLabel:
    """
    Farklı modellerin etiket formatlarını ortak etikete çevirir.

    Desteklenenler: "positive"/"neg"/"Neutral", 3 sınıflı "LABEL_0..2"
    (cardiffnlp) ve 5 yıldızlı "1 star".."5 stars" (nlptown).
    """
    label = raw_label.strip().lower()
    if label.startswith(("pos", "label_2")):
        return SentimentLabel.POSITIVE
    if label.startswith(("neg", "label_0")):
        return SentimentLabel.NEGATIVE
    if label.startswith(("neu", "label_1")):
        return SentimentLabel.NEUTRAL

    stars = re.match(r"^(\d)\s*star", label)
    if stars:
        value = int(stars.group(1))
        if value <= 2:
            return SentimentLabel.NEGATIVE
        return SentimentLabel.NEUTRAL if value == 3 else SentimentLabel.POSITIVE

    logger.warning("Bilinmeyen model etiketi '%s', nötr kabul edildi.", raw_label)
    return SentimentLabel.NEUTRAL


class LexiconSentimentAnalyzer(SentimentAnalyzer):
    """Olumsuzlama farkındalığı olan basit sözlük tabanlı analizci (TR + EN)."""

    name = "lexicon"
    _NEGATION_WINDOW = 3

    def predict(self, texts: list[str]) -> list[SentimentPrediction]:
        return [self._score(text) for text in texts]

    def _score(self, text: str) -> SentimentPrediction:
        tokens = [t.lower() for t in _TOKEN_RE.findall(text or "")]
        positive = negative = 0
        for index, token in enumerate(tokens):
            polarity = 1 if token in POSITIVE_WORDS else -1 if token in NEGATIVE_WORDS else 0
            if polarity and self._is_negated(tokens, index):
                polarity = -polarity
            positive += polarity > 0
            negative += polarity < 0

        hits = positive + negative
        if hits == 0 or positive == negative:
            return _EMPTY_PREDICTION
        label = SentimentLabel.POSITIVE if positive > negative else SentimentLabel.NEGATIVE
        confidence = 0.5 + 0.5 * abs(positive - negative) / hits
        return SentimentPrediction(label=label, score=round(min(confidence, 0.99), 4))

    def _is_negated(self, tokens: list[str], index: int) -> bool:
        before = tokens[max(0, index - self._NEGATION_WINDOW): index]
        after = tokens[index + 1: index + 1 + self._NEGATION_WINDOW]
        return any(t in NEGATORS_BEFORE for t in before) or any(t in NEGATORS_AFTER for t in after)


class HuggingFaceSentimentAnalyzer(SentimentAnalyzer):
    """HuggingFace `text-classification` pipeline'ı ile toplu (batch) tahmin."""

    name = "huggingface"

    def __init__(self, model_name: str, batch_size: int = 16):
        # Ağır kütüphaneler yalnızca bu strateji seçildiğinde yüklenir
        import torch
        from transformers import pipeline

        device = 0 if torch.cuda.is_available() else -1
        logger.info("Duygu modeli yükleniyor: %s (%s)", model_name, "GPU" if device == 0 else "CPU")
        self._pipeline = pipeline("text-classification", model=model_name, tokenizer=model_name, device=device)
        self._batch_size = batch_size
        self.model_name = model_name

    def predict(self, texts: list[str]) -> list[SentimentPrediction]:
        results: list[SentimentPrediction] = [_EMPTY_PREDICTION] * len(texts)
        indexed = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not indexed:
            return results

        outputs = self._pipeline(
            [t for _, t in indexed], batch_size=self._batch_size, truncation=True, max_length=512
        )
        for (index, _), output in zip(indexed, outputs):
            results[index] = SentimentPrediction(
                label=normalize_label(output["label"]), score=round(float(output["score"]), 4)
            )
        return results
