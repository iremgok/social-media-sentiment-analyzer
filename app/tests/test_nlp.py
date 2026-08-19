from unittest.mock import patch, MagicMock
from app.api.nlp.preprocessor import TextPreprocessor
from app.api.nlp.sentiment import SentimentAnalyzer


def test_preprocessor_cleans_urls_and_emojis():
    preprocessor = TextPreprocessor()
    raw = "Visit https://google.com for info! Great phone 😀 #cool"
    cleaned = preprocessor.clean(raw)

    assert "https://google.com" not in cleaned
    assert "grinning face" in cleaned
    assert "#" not in cleaned


@patch("app.api.nlp.sentiment.pipeline")
def test_sentiment_analyzer_batch(mock_pipeline):
    # Setup mock classifier
    mock_classifier = MagicMock()
    mock_classifier.return_value = [
        {"label": "positive", "score": 0.99},
        {"label": "negative", "score": 0.98}
    ]
    mock_pipeline.return_value = mock_classifier

    # Instantiate SentimentAnalyzer (this triggers mock_pipeline)
    analyzer = SentimentAnalyzer()

    texts = ["I love this product, it is amazing!", "Worst experience ever, totally broken."]
    results = analyzer.analyze_batch(texts)

    assert len(results) == 2
    assert results[0]["label"] == "positive"
    assert results[1]["label"] == "negative"
    
    # Assert model was called with inputs
    mock_classifier.assert_called_once_with(
        ["I love this product, it is amazing!", "Worst experience ever, totally broken."],
        batch_size=32
    )