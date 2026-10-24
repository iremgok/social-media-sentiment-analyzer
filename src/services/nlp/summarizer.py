"""
Özetleme stratejileri.

  * `ExtractiveSummarizer`   – istatistik + anahtar kelime + temsilci yorum seçimiyle
                               model gerektirmeden 1-2 paragraflık genel görüş üretir.
  * `HuggingFaceSummarizer`  – olumlu/olumsuz yorum kümelerini seq2seq modeliyle
                               soyutlayıcı (abstractive) olarak özetler.

OpenAI tabanlı özetleyici `openai_backend.py` içindedir.
"""

import re
from abc import ABC, abstractmethod
from collections import Counter

from src.core.logger import get_logger
from src.models.schemas import AnalysisSummary, CommentResult, SentimentDistribution, SentimentLabel
from src.services.nlp.lexicon import NEGATIVE_WORDS, POSITIVE_WORDS, STOPWORDS

logger = get_logger(__name__)

_WORD_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_LANGUAGE_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca", "es": "İspanyolca"}
_TONE_THRESHOLD = 15.0  # yüzde puanı
_MIN_WORDS_FOR_ABSTRACTIVE = 40


class Summarizer(ABC):
    """Analiz edilmiş yorumlardan genel görüş özeti üreten strateji arayüzü."""

    name: str

    @abstractmethod
    def summarize(
        self, query: str, distribution: SentimentDistribution, comments: list[CommentResult]
    ) -> AnalysisSummary:
        ...


class ExtractiveSummarizer(Summarizer):
    """Kural tabanlı, deterministik ve bağımlılıksız özetleyici."""

    name = "extractive"

    def summarize(
        self, query: str, distribution: SentimentDistribution, comments: list[CommentResult]
    ) -> AnalysisSummary:
        positives = self._by_label(comments, SentimentLabel.POSITIVE)
        negatives = self._by_label(comments, SentimentLabel.NEGATIVE)
        return AnalysisSummary(
            overview=self.build_overview(query, distribution, comments, positives, negatives),
            positive_highlights=self.highlights(positives) or "Belirgin bir olumlu geri bildirim bulunamadı.",
            negative_highlights=self.highlights(negatives) or "Belirgin bir olumsuz geri bildirim bulunamadı.",
        )

    # ---- Yardımcılar (alt sınıflar tarafından da kullanılır) ---------------- #
    @staticmethod
    def _by_label(comments: list[CommentResult], label: SentimentLabel) -> list[CommentResult]:
        selected = [c for c in comments if c.label == label and c.cleaned_text]
        return sorted(selected, key=lambda c: c.score, reverse=True)

    def build_overview(
        self,
        query: str,
        dist: SentimentDistribution,
        comments: list[CommentResult],
        positives: list[CommentResult],
        negatives: list[CommentResult],
    ) -> str:
        if dist.total == 0:
            return f"'{query}' için analiz edilecek yorum bulunamadı."

        diff = dist.positive_pct - dist.negative_pct
        if diff > _TONE_THRESHOLD:
            tone = "belirgin biçimde olumlu"
        elif diff < -_TONE_THRESHOLD:
            tone = "belirgin biçimde olumsuz"
        else:
            tone = "karışık ve dengeli"

        first = (
            f"'{query}' hakkında {dist.total} yorum analiz edildi. Dağılım: %{dist.positive_pct:g} olumlu, "
            f"%{dist.negative_pct:g} olumsuz ve %{dist.neutral_pct:g} nötr. "
            f"Kullanıcıların genel algısı {tone} görünüyor."
        )
        language = self._dominant_language(comments)
        if language:
            first += f" Yorumların çoğunluğu {language} yazılmış."

        query_tokens = {t.lower() for t in _WORD_RE.findall(query)}
        pos_terms = self.keywords(positives, exclude=query_tokens)
        neg_terms = self.keywords(negatives, exclude=query_tokens)
        parts = []
        if pos_terms:
            parts.append(f"Olumlu yorumlarda en çok öne çıkan konular: {', '.join(pos_terms)}.")
        if neg_terms:
            parts.append(f"Eleştirilerde ise {', '.join(neg_terms)} gibi başlıklar sıkça dile getiriliyor.")
        return first if not parts else f"{first}\n\n{' '.join(parts)}"

    @staticmethod
    def keywords(comments: list[CommentResult], exclude: set[str], top_n: int = 5) -> list[str]:
        """Duygu kelimeleri ve durak kelimeler dışındaki en sık konu terimlerini döndürür."""
        ignored = STOPWORDS | POSITIVE_WORDS | NEGATIVE_WORDS | exclude
        counter: Counter[str] = Counter()
        for comment in comments:
            # Aynı yorumdaki tekrarlar tek sayılır; terim yaygınlığı ölçülür
            counter.update({w for w in (t.lower() for t in _WORD_RE.findall(comment.cleaned_text)) if w not in ignored})
        return [word for word, count in counter.most_common(top_n) if count > 1 or len(comments) <= 2]

    @staticmethod
    def highlights(comments: list[CommentResult], top_n: int = 3) -> str:
        """En yüksek güvenli, birbirinden farklı yorumları madde listesi olarak döndürür."""
        seen: set[str] = set()
        picked = []
        for comment in comments:
            key = " ".join(_WORD_RE.findall(comment.cleaned_text.lower()))[:50]
            if key not in seen:
                seen.add(key)
                picked.append(f"• {comment.cleaned_text}")
            if len(picked) == top_n:
                break
        return "\n".join(picked)

    @staticmethod
    def _dominant_language(comments: list[CommentResult]) -> str:
        known = Counter(c.language for c in comments if c.language != "unknown")
        if not known:
            return ""
        code, _ = known.most_common(1)[0]
        return _LANGUAGE_NAMES.get(code, code)


class HuggingFaceSummarizer(ExtractiveSummarizer):
    """Olumlu/olumsuz kümeleri seq2seq modeliyle özetler; kısa kümelerde çıkarımsal özete düşer."""

    name = "huggingface"

    def __init__(self, model_name: str):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Özetleme modeli yükleniyor: %s (%s)", model_name, self._device)
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self._device)
        self._model.eval()

    def summarize(
        self, query: str, distribution: SentimentDistribution, comments: list[CommentResult]
    ) -> AnalysisSummary:
        base = super().summarize(query, distribution, comments)
        positives = self._by_label(comments, SentimentLabel.POSITIVE)
        negatives = self._by_label(comments, SentimentLabel.NEGATIVE)
        return base.model_copy(update={
            "positive_highlights": self._abstractive(positives) or base.positive_highlights,
            "negative_highlights": self._abstractive(negatives) or base.negative_highlights,
        })

    def _abstractive(self, comments: list[CommentResult]) -> str:
        blob = " ".join(c.cleaned_text.rstrip(".!?") + "." for c in comments[:15])
        if len(blob.split()) < _MIN_WORDS_FOR_ABSTRACTIVE:
            return ""
        try:
            inputs = self._tokenizer(blob, max_length=1024, truncation=True, return_tensors="pt").to(self._device)
            with self._torch.no_grad():
                ids = self._model.generate(
                    inputs["input_ids"], num_beams=4, max_length=120, min_length=30,
                    no_repeat_ngram_size=3, early_stopping=True,
                )
            return self._tokenizer.decode(ids[0], skip_special_tokens=True).strip()
        except Exception as exc:  # Model hatası tüm analizi düşürmemeli
            logger.error("Soyutlayıcı özet üretilemedi: %s", exc)
            return ""
