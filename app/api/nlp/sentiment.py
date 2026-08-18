from typing import Dict,List, Union
from transformers import pipeline
import torch

class SentimentAnalyzer:
    """
    HuggingFace modelini kullanarak metinden duygu analizi yapar.
    """

    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):

        self.device = 0 if torch.cuda.is_available() else -1
        print(f"Model Yükleniyor: {model_name} (Device: {'Gpu' if self.device == 0 else 'CPU'}")

        self.classifier = pipeline(
            "sentiment-analysis",
            model=model_name,
            tokenizer=model_name,
            device=self.device,
            truncation=True,
            max_length=512
        )

    def analyze_single(self, text: str) -> Dict[str, Union[str, float]]:
        """Tek bir metin için duygu analizi yapar."""
        if not text or not text.strip():
            return {"label": "neutral", "score": 0.0}

        result = self.classifier(text)[0]
        return {
            "label": result["label"].lower(),
            "score": round(float(result["score"]), 4)
        }

    def analyze_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, Union[str, float]]]:
        """
        Birden fazla metni toplu (batch) olarak işler.
        Döngüyle tek tek çağırmaktan kat kat daha hızlıdır.
        """
        if not texts:
            return []

        # Boş olmayan metinleri filtrele
        valid_texts = [t if t.strip() else "neutral" for t in texts]

        results = self.classifier(valid_texts, batch_size=batch_size)

        formatted_results = []
        for res in results:
            formatted_results.append({
                "label": res["label"].lower(),
                "score": round(float(res["score"]), 4)
            })

        return formatted_results

    def get_summary_metrics(self, analysis_results: List[Dict[str, Union[str, float]]]) -> Dict[str, float]:
        """
        Analiz sonuçlarının yüzdelik dağılımını hesaplar.
        """
        total = len(analysis_results)
        if total == 0:
            return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

        counts = {"positive": 0, "negative": 0, "neutral": 0}
        for item in analysis_results:
            label = item["label"]
            if label in counts:
                counts[label] += 1

        return {
            "positive_pct": round((counts["positive"] / total) * 100, 2),
            "negative_pct": round((counts["negative"] / total) * 100, 2),
            "neutral_pct": round((counts["neutral"] / total) * 100, 2),
            "total_comments": total
        }


# --- TEST BLOĞU (Girintisiz, en solda olmalı) ---
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    sample_comments = [
        "This update completely ruined the camera performance.",
        "Honestly, I'm very impressed with the battery life! Highly recommend.",
        "The package arrived today. Nothing special."
    ]

    print("\n--- Batch Analiz Sonuçları ---")
    predictions = analyzer.analyze_batch(sample_comments)
    for text, pred in zip(sample_comments, predictions):
        print(f"Yorum: {text}\nSonuç: {pred['label']} (Güven: {pred['score']})\n")

    metrics = analyzer.get_summary_metrics(predictions)
    print("--- Genel Dağılım ---")
    print(metrics)



