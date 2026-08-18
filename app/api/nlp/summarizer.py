from typing import Dict, List
from transformers import pipeline
import torch


class TextSummarizer:
    """
    Hafif açık kaynak modeller (DistilBART) kullanarak
    toplanan yorumlardan ana fikirleri özetleyen sınıf.
    """

    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        self.device = 0 if torch.cuda.is_available() else -1
        print(f"Özetleme modeli yükleniyor: {model_name} (Device: {'GPU' if self.device == 0 else 'CPU'})")

        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name,
            device=self.device
        )

    def summarize_text(self, text: str, max_length: int = 60, min_length: int = 15) -> str:
        """Uzun bir metin bloğunu özetler."""
        if not text or len(text.split()) < 15:
            # Metin çok kısaysa modeli yormadan direkt metni döndür
            return text.strip()

        try:
            summary = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,
                truncation=True
            )
            return summary[0]["summary_text"].strip()
        except Exception as e:
            return f"Özet çıkarılamadı: {str(e)}"

    def summarize_feedback_by_sentiment(
        self,
        comments_with_sentiment: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Duygu analizine göre ayrılmış yorumları pozitif ve negatif
        olarak iki ayrı odak özetine dönüştürür.
        """
        positives = [item["text"] for item in comments_with_sentiment if item.get("label") == "positive"]
        negatives = [item["text"] for item in comments_with_sentiment if item.get("label") == "negative"]

        # En fazla ilk 10 yorumu birleştirerek context limitini aşmayı engelle
        pos_blob = " ".join(positives[:10])
        neg_blob = " ".join(negatives[:10])

        pos_summary = self.summarize_text(pos_blob) if pos_blob else "Yeterli pozitif geri bildirim yok."
        neg_summary = self.summarize_text(neg_blob) if neg_blob else "Yeterli negatif geri bildirim yok."

        return {
            "positive_summary": pos_summary,
            "negative_summary": neg_summary
        }


# --- TEST BLOĞU (Girintisiz, en solda) ---
if __name__ == "__main__":
    summarizer = TextSummarizer()

    sample_feedbacks = [
        {"text": "The camera quality on this device is stunning, crystal clear night shots.", "label": "positive"},
        {"text": "Screen colors and 120Hz refresh rate make everything feel super smooth.", "label": "positive"},
        {"text": "Battery drains in less than 5 hours of moderate use, very disappointed.", "label": "negative"},
        {"text": "Device gets dangerously hot while charging and playing games.", "label": "negative"}
    ]

    print("\n--- Özetleme Sonucu ---")
    summaries = summarizer.summarize_feedback_by_sentiment(sample_feedbacks)
    print("Pozitif Noktalar:", summaries["positive_summary"])
    print("Negatif Şikayetler:", summaries["negative_summary"])