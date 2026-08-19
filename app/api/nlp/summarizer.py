from typing import Dict, List
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class TextSummarizer:
    """
    AutoModelForSeq2SeqLM kullanarak özetleme yapan sınıf.
    Pipeline registry hatalarını tamamen engeller.
    """

    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Özetleme modeli yükleniyor: {model_name} (Device: {self.device})")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)

    def summarize_text(self, text: str, max_length: int = 60, min_length: int = 15) -> str:
        """Uzun bir metin bloğunu özetler."""
        if not text or len(text.split()) < 15:
            return text.strip() if text else ""

        try:
            inputs = self.tokenizer(
                text,
                max_length=1024,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)

            summary_ids = self.model.generate(
                inputs["input_ids"],
                num_beams=4,
                max_length=max_length,
                min_length=min_length,
                early_stopping=True,
                no_repeat_ngram_size=3
            )

            return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
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

        pos_blob = " ".join(positives[:10])
        neg_blob = " ".join(negatives[:10])

        pos_summary = self.summarize_text(pos_blob) if pos_blob else "Yeterli pozitif geri bildirim yok."
        neg_summary = self.summarize_text(neg_blob) if neg_blob else "Yeterli negatif geri bildirim yok."

        return {
            "positive_summary": pos_summary,
            "negative_summary": neg_summary
        }


if __name__ == "__main__":
    summarizer = TextSummarizer()
    test_text = (
        "The battery life of this smartphone is really amazing and lasts two full days. "
        "The screen colors are very sharp and vibrant. The camera takes stunning pictures at night. "
        "However, charging is somewhat slow."
    )
    print("Özet:", summarizer.summarize_text(test_text))