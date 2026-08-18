from app.nlp.preprocessor import TextPreprocessor
from app.nlp.sentiment import SentimentAnalyzer


def test_preprocessor_cleans_urls_and_emojis():
    preprocessor = TextPreprocessor()
    raw = "Visit https://google.com for info! Great phone 😀 #cool"
    cleaned = preprocessor.clean(raw)

    assert "https://google.com" not in cleaned
    assert "grinning face" in cleaned
    assert "#" not in cleaned


def test_sentiment_analyzer_batch():
    analyzer = SentimentAnalyzer()
    texts = ["I love this product, it is amazing!", "Worst experience ever, totally broken."]
    results = analyzer.analyze_batch(texts)

    assert len(results) == 2
    assert results[0]["label"] == "positive"
    assert results[1]["label"] == "negative"