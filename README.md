# 📊 Sosyal Medya Yorum Analizi ve Özetleme Aracı

Twitter/X ve Reddit'ten hashtag veya anahtar kelimeye göre güncel yorumları toplayan, bunları
**Olumlu / Olumsuz / Nötr** olarak sınıflandıran, kullanıcıların genel görüşünü 1-2 paragrafta
özetleyen ve sonuçları geçmişiyle birlikte saklayan uçtan uca bir NLP uygulaması.

- **Backend:** FastAPI (REST, Pydantic doğrulama, Swagger UI)
- **NLP:** HuggingFace Transformers **veya** OpenAI API, ikisi de yoksa hafif sözlük tabanlı mod
- **Kalıcılık:** SQLAlchemy 2.0 ile SQLite (varsayılan) veya PostgreSQL
- **Arayüz:** Streamlit + Plotly dashboard
- **API anahtarı gerekmez:** Anahtar yoksa ya da API hata verirse akıllı mock veri üreteci devreye girer

---

## 🏗️ Mimari

```text
src/
├── core/                  # Konfigürasyon (pydantic-settings) ve merkezi loglama
├── models/
│   ├── schemas.py         # Pydantic istek/yanıt modelleri (katmanlar arası ortak dil)
│   └── orm.py             # SQLAlchemy tabloları
├── services/
│   ├── scraper_service.py # Platform seçimi + mock'a otomatik düşme (facade)
│   ├── scrapers/          # twitter.py · reddit.py · mock.py  (Strategy pattern)
│   ├── nlp_service.py     # Ön işleme → sınıflandırma → metrikler → özet (facade + fallback)
│   ├── nlp/               # preprocessor · sentiment · summarizer · openai_backend · lexicon
│   ├── db_service.py      # Repository: kaydet / listele / getir / sil
│   └── analysis_service.py# Use case: scraper + NLP + DB akışını birleştirir
├── api/
│   ├── dependencies.py    # Servis container'ı ve dependency injection
│   └── routes.py          # /analyze, /history, /health endpoint'leri
├── ui/
│   ├── app.py             # Streamlit dashboard (giriş noktası)
│   ├── components.py      # Yeniden kullanılabilir UI bileşenleri
│   ├── charts.py          # Plotly grafik fabrikaları
│   └── api_client.py      # Backend HTTP istemcisi
└── main.py                # FastAPI uygulama fabrikası
tests/                     # pytest: API uçtan uca, NLP ve scraper testleri
```

**Bağımlılık yönü:** `ui → (HTTP) → api → services → models/core`. Route'lar iş mantığı içermez,
servisler HTTP bilmez, UI veritabanına veya modellere doğrudan erişmez.

**Dayanıklılık (graceful degradation):**

| Durum | Davranış |
|---|---|
| Twitter/Reddit anahtarı yok, API hata/limit verdi, sonuç boş | Mock veri (`is_mock_data: true`) |
| HuggingFace modeli indirilemedi / yüklenemedi | Sözlük tabanlı analizci |
| OpenAI isteği çalışma anında başarısız | O istek için sözlük analizcisi + çıkarımsal özet |
| Veritabanına yazılamadı | Sonuç yine döner, hata loglanır |

---

## 🚀 Kurulum

### 1) Yerel ortam

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # anahtarları isteğe bağlı olarak doldurun
```

> Yalnızca CPU varsa daha küçük torch için:
> `pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt`

```bash
# Terminal 1 – Backend  (http://localhost:8000/docs)
uvicorn src.main:app --reload

# Terminal 2 – Dashboard (http://localhost:8501)
streamlit run src/ui/app.py
```

Model indirmeden hızlıca denemek için `.env` içinde `NLP_PROVIDER=lexicon` yapın.

### 2) Docker

```bash
cp .env.example .env
docker compose up --build
```

Backend `8000`, dashboard `8501` portundadır. Veritabanı ve HuggingFace model önbelleği
volume'larda saklanır; modeller yalnızca ilk açılışta indirilir.

---

## ⚙️ Konfigürasyon

Tüm ayarlar `.env` üzerinden okunur ve açılışta doğrulanır (bkz. `.env.example`).

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `NLP_PROVIDER` | `auto` · `huggingface` · `openai` · `lexicon` | `auto` |
| `SENTIMENT_MODEL_NAME` | HF sınıflandırma modeli (3 sınıflı veya 1-5 yıldız modelleri desteklenir) | `cardiffnlp/twitter-xlm-roberta-base-sentiment` |
| `SUMMARIZER_MODEL_NAME` | HF seq2seq özetleme modeli | `sshleifer/distilbart-cnn-12-6` |
| `ENABLE_ABSTRACTIVE_SUMMARY` | `false` ise özetleme modeli yüklenmez | `true` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI sınıflandırma + özet | – / `gpt-4o-mini` |
| `TWITTER_BEARER_TOKEN` | X API v2 recent search | – |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | PRAW kimlik bilgileri | – |
| `DATABASE_URL` | SQLAlchemy bağlantı adresi | `sqlite:///./data/sentiment_analyzer.db` |

> `nlptown/bert-base-multilingual-uncased-sentiment` gibi 5 yıldızlı modeller otomatik olarak
> 1-2★ = olumsuz, 3★ = nötr, 4-5★ = olumlu şeklinde eşlenir.

---

## 🔌 API

| Metot | Yol | Açıklama |
|---|---|---|
| `POST` | `/api/v1/analyze` | Yeni analiz (201 Created) |
| `GET` | `/api/v1/history?limit=&offset=&query=` | Sayfalı geçmiş listesi |
| `GET` | `/api/v1/history/{id}` | Analiz detayı (tüm yorumlar dahil) |
| `DELETE` | `/api/v1/history/{id}` | Analizi sil (204) |
| `GET` | `/api/v1/health` | Servis, veritabanı ve kaynak durumu |

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "#iPhone15", "platform": "twitter", "limit": 30}'
```

Yanıt; duygu dağılımını (`distribution`), yapay zeka özetini (`summary.overview`,
`positive_highlights`, `negative_highlights`), dil dağılımını ve sınıflandırılmış yorumları içerir.

---

## 🧪 Testler

```bash
pytest
```

Testler ağ erişimi veya model indirmesi gerektirmez: `lexicon` NLP modu, mock veri ve geçici
bir SQLite veritabanı kullanılır.
