"""
NLP servisi: ön işleme → duygu analizi → metrikler → özetleme.

Seçilen sağlayıcı (HuggingFace / OpenAI) yüklenemezse veya çalışma anında
hata verirse sözlük tabanlı analizciye ve çıkarımsal özetleyiciye düşer;
böylece API hiçbir koşulda NLP yüzünden çökmez.
"""

from collections import Counter
from dataclasses import dataclass

from src.core.config import NLPProvider, Settings
from src.core.logger import get_logger
from src.models.schemas import (
    AnalysisSummary,
    CommentResult,
    RawComment,
    SentimentDistribution,
    SentimentLabel,
    SentimentPrediction,
)
from src.services.nlp import (
    ExtractiveSummarizer,
    HuggingFaceSentimentAnalyzer,
    HuggingFaceSummarizer,
    LexiconSentimentAnalyzer,
    SentimentAnalyzer,
    Summarizer,
    TextPreprocessor,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class NLPResult:
    comments: list[CommentResult]
    distribution: SentimentDistribution
    summary: AnalysisSummary
    languages: dict[str, int]
    provider: str


def compute_distribution(labels: list[SentimentLabel]) -> SentimentDistribution:
    """Etiket listesinden adet ve yüzde dağılımı hesaplar."""
    total = len(labels)
    counts = Counter(labels)

    def pct(label: SentimentLabel) -> float:
        return round(counts[label] / total * 100, 2) if total else 0.0

    return SentimentDistribution(
        total=total,
        positive=counts[SentimentLabel.POSITIVE],
        negative=counts[SentimentLabel.NEGATIVE],
        neutral=counts[SentimentLabel.NEUTRAL],
        positive_pct=pct(SentimentLabel.POSITIVE),
        negative_pct=pct(SentimentLabel.NEGATIVE),
        neutral_pct=pct(SentimentLabel.NEUTRAL),
    )


class NLPService:
    """Ön işleme, sınıflandırma ve özetleme stratejilerini koordine eden cephe."""

    def __init__(
        self,
        preprocessor: TextPreprocessor,
        analyzer: SentimentAnalyzer,
        summarizer: Summarizer,
        fallback_analyzer: SentimentAnalyzer | None = None,
        fallback_summarizer: Summarizer | None = None,
    ):
        self._preprocessor = preprocessor
        self._analyzer = analyzer
        self._summarizer = summarizer
        self._fallback_analyzer = fallback_analyzer or LexiconSentimentAnalyzer()
        self._fallback_summarizer = fallback_summarizer or ExtractiveSummarizer()

    @property
    def provider_name(self) -> str:
        return self._analyzer.name

    @classmethod
    def from_settings(cls, settings: Settings) -> "NLPService":
        analyzer, summarizer = _build_strategies(settings)
        return cls(TextPreprocessor(), analyzer, summarizer)

    def analyze(self, query: str, raw_comments: list[RawComment]) -> NLPResult:
        processed = self._preprocessor.process_batch([c.text for c in raw_comments])
        predictions, provider = self._predict([p.cleaned for p in processed])

        comments = [
            CommentResult(
                external_id=raw.id,
                original_text=raw.text,
                cleaned_text=prep.cleaned,
                language=prep.language,
                label=pred.label,
                score=pred.score,
                author=raw.author,
                created_at=raw.created_at,
            )
            for raw, prep, pred in zip(raw_comments, processed, predictions)
        ]
        distribution = compute_distribution([c.label for c in comments])
        return NLPResult(
            comments=comments,
            distribution=distribution,
            summary=self._summarize(query, distribution, comments),
            languages=dict(Counter(c.language for c in comments).most_common()),
            provider=provider,
        )

    def _predict(self, texts: list[str]) -> tuple[list[SentimentPrediction], str]:
        try:
            predictions = self._analyzer.predict(texts)
            if len(predictions) != len(texts):
                raise ValueError("Tahmin sayısı girdi sayısıyla eşleşmiyor.")
            return predictions, self._analyzer.name
        except Exception as exc:
            logger.error("'%s' analizcisi başarısız (%s); sözlük analizine geçiliyor.", self._analyzer.name, exc)
            return self._fallback_analyzer.predict(texts), self._fallback_analyzer.name

    def _summarize(
        self, query: str, distribution: SentimentDistribution, comments: list[CommentResult]
    ) -> AnalysisSummary:
        try:
            return self._summarizer.summarize(query, distribution, comments)
        except Exception as exc:
            logger.error("'%s' özetleyicisi başarısız (%s); çıkarımsal özete geçiliyor.", self._summarizer.name, exc)
            return self._fallback_summarizer.summarize(query, distribution, comments)


def _build_strategies(settings: Settings) -> tuple[SentimentAnalyzer, Summarizer]:
    """Ayarlara göre stratejileri oluşturur; yüklenemeyenleri hafif yedeklerle değiştirir."""
    provider = settings.resolved_nlp_provider
    logger.info("NLP sağlayıcısı: %s", provider.value)

    if provider is NLPProvider.OPENAI:
        if not settings.OPENAI_API_KEY:
            logger.warning("NLP_PROVIDER=openai fakat OPENAI_API_KEY yok; lexicon moduna geçiliyor.")
        else:
            try:
                from src.services.nlp.openai_backend import OpenAISentimentAnalyzer, OpenAISummarizer

                args = (settings.OPENAI_API_KEY, settings.OPENAI_MODEL, settings.OPENAI_TIMEOUT_SECONDS)
                return OpenAISentimentAnalyzer(*args), OpenAISummarizer(*args)
            except ImportError as exc:
                logger.error("openai paketi yüklenemedi (%s); lexicon moduna geçiliyor.", exc)

    if provider is NLPProvider.HUGGINGFACE:
        try:
            analyzer = HuggingFaceSentimentAnalyzer(settings.SENTIMENT_MODEL_NAME, settings.SENTIMENT_BATCH_SIZE)
        except Exception as exc:  # ImportError, ağ hatası, bozuk model vb.
            logger.error("HuggingFace duygu modeli yüklenemedi (%s); lexicon moduna geçiliyor.", exc)
            return LexiconSentimentAnalyzer(), ExtractiveSummarizer()
        return analyzer, _build_hf_summarizer(settings)

    return LexiconSentimentAnalyzer(), ExtractiveSummarizer()


def _build_hf_summarizer(settings: Settings) -> Summarizer:
    if not settings.ENABLE_ABSTRACTIVE_SUMMARY:
        return ExtractiveSummarizer()
    try:
        return HuggingFaceSummarizer(settings.SUMMARIZER_MODEL_NAME)
    except Exception as exc:
        logger.error("Özetleme modeli yüklenemedi (%s); çıkarımsal özet kullanılacak.", exc)
        return ExtractiveSummarizer()
