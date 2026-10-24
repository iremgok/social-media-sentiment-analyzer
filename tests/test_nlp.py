"""Ön işleme, duygu analizi ve özetleme birim testleri."""

from unittest.mock import MagicMock

import pytest

from src.models.schemas import Platform, RawComment, SentimentLabel, SentimentPrediction
from src.services.nlp import ExtractiveSummarizer, LexiconSentimentAnalyzer, TextPreprocessor, normalize_label
from src.services.nlp_service import NLPService, compute_distribution


# --------------------------- Ön işleme ------------------------------------ #
def test_preprocessor_removes_noise_and_keeps_hashtag_word():
    cleaned = TextPreprocessor().clean("RT @user Harika telefon!!! https://t.co/x #iPhone15 &amp; 😍   çooooook")
    assert "https://" not in cleaned
    assert "@user" not in cleaned
    assert "#" not in cleaned and "iPhone15" in cleaned
    assert "&" in cleaned and "😍" in cleaned
    assert "çooo" in cleaned and "çoooo" not in cleaned
    assert not cleaned.startswith("RT")


def test_preprocessor_handles_empty_input():
    assert TextPreprocessor().clean("") == ""
    assert TextPreprocessor().clean(None) == ""  # type: ignore[arg-type]


def test_language_detection():
    pre = TextPreprocessor()
    assert pre.detect_language("Bu telefon gerçekten çok güzel, herkese tavsiye ederim.") == "tr"
    assert pre.detect_language("This phone is really great, I recommend it to everyone.") == "en"
    assert pre.detect_language("ok") == "unknown"


# --------------------------- Duygu analizi -------------------------------- #
@pytest.mark.parametrize("raw, expected", [
    ("positive", SentimentLabel.POSITIVE), ("Negative", SentimentLabel.NEGATIVE),
    ("neutral", SentimentLabel.NEUTRAL), ("LABEL_0", SentimentLabel.NEGATIVE),
    ("LABEL_2", SentimentLabel.POSITIVE), ("1 star", SentimentLabel.NEGATIVE),
    ("3 stars", SentimentLabel.NEUTRAL), ("5 stars", SentimentLabel.POSITIVE),
])
def test_normalize_label(raw, expected):
    assert normalize_label(raw) == expected


@pytest.mark.parametrize("text, expected", [
    ("This is amazing, I love it!", SentimentLabel.POSITIVE),
    ("Worst purchase ever, totally broken.", SentimentLabel.NEGATIVE),
    ("The package arrived today.", SentimentLabel.NEUTRAL),
    ("Ürün harika, çok memnunum 😍", SentimentLabel.POSITIVE),
    ("Hiç memnun değilim, berbat bir deneyim.", SentimentLabel.NEGATIVE),
    ("This is not good at all", SentimentLabel.NEGATIVE),
])
def test_lexicon_analyzer(text, expected):
    assert LexiconSentimentAnalyzer().predict([text])[0].label == expected


def test_compute_distribution():
    dist = compute_distribution([SentimentLabel.POSITIVE] * 2 + [SentimentLabel.NEGATIVE])
    assert (dist.total, dist.positive, dist.negative, dist.neutral) == (3, 2, 1, 0)
    assert dist.positive_pct == 66.67 and dist.dominant == SentimentLabel.POSITIVE
    assert compute_distribution([]).total == 0


# --------------------------- Servis cephesi ------------------------------- #
def _raw(texts):
    return [RawComment(id=str(i), text=t, platform=Platform.MOCK) for i, t in enumerate(texts)]


def test_nlp_service_falls_back_when_primary_fails():
    broken = MagicMock(name="broken")
    broken.name = "huggingface"
    broken.predict.side_effect = RuntimeError("CUDA out of memory")
    service = NLPService(TextPreprocessor(), broken, ExtractiveSummarizer())

    result = service.analyze("Phone", _raw(["I love it, amazing!", "Terrible and slow."]))
    assert result.provider == "lexicon"
    assert [c.label for c in result.comments] == [SentimentLabel.POSITIVE, SentimentLabel.NEGATIVE]


def test_nlp_service_uses_primary_predictions():
    primary = MagicMock()
    primary.name = "openai"
    primary.predict.return_value = [SentimentPrediction(label=SentimentLabel.NEGATIVE, score=0.9)]
    service = NLPService(TextPreprocessor(), primary, ExtractiveSummarizer())

    result = service.analyze("X", _raw(["whatever"]))
    assert result.provider == "openai"
    assert result.distribution.negative == 1


def test_extractive_summary_contains_overview_and_highlights():
    service = NLPService(TextPreprocessor(), LexiconSentimentAnalyzer(), ExtractiveSummarizer())
    texts = [
        "Battery life is amazing", "Great battery and amazing screen",
        "Camera is terrible", "Terrible camera quality, awful", "Arrived today",
    ]
    summary = service.analyze("Pixel", _raw(texts)).summary
    assert "'Pixel'" in summary.overview and "5 yorum analiz edildi" in summary.overview
    assert "battery" in summary.overview and "camera" in summary.overview
    assert summary.positive_highlights.startswith("•")
    assert summary.negative_highlights.startswith("•")
