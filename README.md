# 📊 Social Media Sentiment & Summarization Pipeline

Uçtan uca sosyal medya kullanıcı yorumlarını toplayan, Hugging Face transformer modelleriyle duygu sınıflandırması yapan ve öne çıkan geri bildirimleri özetleyerek Streamlit üzerinde interaktif sunan veri analitiği aracı.

---

## 🏗️ Mimari & Veri Akışı

```text
[Reddit / X API] 
       │
       ▼
[TextPreprocessor] ──▶ (Regex, Emoji Demojize, Temizleme)
       │
       ▼
[SentimentAnalyzer] ─▶ (cardiffnlp/twitter-roberta-base-sentiment-latest)
       │
       ▼
[TextSummarizer] ────▶ (sshleifer/distilbart-cnn-12-6)
       │
       ▼
[FastAPI Backend] ───▶ (REST Endpoints / Swagger UI - Port 8000)
       │
       ▼
[Streamlit UI] ──────▶ (Plotly Dağılım Grafikleri & Özet Kartları - Port 8501)