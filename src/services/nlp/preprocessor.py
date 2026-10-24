"""Yorum metinleri için temizlik ve dil tespiti."""

import html
import re
from dataclasses import dataclass

from src.core.logger import get_logger

logger = get_logger(__name__)

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"(?<!\w)@\w+")
_HASHTAG_RE = re.compile(r"#(\w+)")
_RT_RE = re.compile(r"^RT\s+", re.IGNORECASE)
_REPEAT_RE = re.compile(r"(.)\1{3,}")         # "çooooook" -> "çoook"
_WHITESPACE_RE = re.compile(r"\s+")
_MIN_LANG_CHARS = 15

try:
    from langdetect import DetectorFactory, LangDetectException, detect

    DetectorFactory.seed = 0  # langdetect varsayılan olarak rastgeledir; sonuçları sabitle
    _LANGDETECT_AVAILABLE = True
except ImportError:  # pragma: no cover - opsiyonel bağımlılık
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect kurulu değil; dil tespiti 'unknown' döndürecek.")


@dataclass(frozen=True)
class PreprocessedText:
    cleaned: str
    language: str


class TextPreprocessor:
    """
    Sosyal medya metinlerini model girdisine hazırlar.

    Emojiler bilinçli olarak korunur: Twitter verisiyle eğitilmiş transformer
    modelleri ve sözlük analizcisi emojileri güçlü duygu sinyali olarak kullanır.
    """

    def __init__(self, keep_hashtag_words: bool = True, max_chars: int = 2000):
        self._keep_hashtag_words = keep_hashtag_words
        self._max_chars = max_chars

    def clean(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        text = html.unescape(text)                    # &amp; -> &
        text = _RT_RE.sub("", text)
        text = _URL_RE.sub(" ", text)
        text = _MENTION_RE.sub(" ", text)
        text = _HASHTAG_RE.sub(r"\1" if self._keep_hashtag_words else " ", text)
        text = _REPEAT_RE.sub(r"\1\1\1", text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text[: self._max_chars]

    @staticmethod
    def detect_language(text: str) -> str:
        """ISO-639-1 dil kodu döndürür; kısa veya belirsiz metinler için 'unknown'."""
        if not _LANGDETECT_AVAILABLE or len(text) < _MIN_LANG_CHARS:
            return "unknown"
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

    def process(self, text: str) -> PreprocessedText:
        cleaned = self.clean(text)
        return PreprocessedText(cleaned=cleaned, language=self.detect_language(cleaned))

    def process_batch(self, texts: list[str]) -> list[PreprocessedText]:
        """Girdi sırasını koruyarak toplu ön işleme yapar."""
        return [self.process(t) for t in texts]
