import sys
from pathlib import Path

# Proje ana dizinini ve dashboard dizinini modül arama yoluna ekle
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px

# Aynı klasörden doğrudan import
try:
    from services import AnalyticsService
except ModuleNotFoundError:
    from app.dashboard.services import AnalyticsService

# Sayfa Konfigürasyonu
st.set_page_config(
    page_title="Sosyal Medya Duygu Analizi & Özetleme",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Sosyal Medya Algı & Duygu Analizi")
st.markdown("Ürün veya anahtar kelimelere ait sosyal medya geri bildirimlerini NLP ile analiz edin.")

# --- Sol Panel (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Arama Parametreleri")
    query_input = st.text_input("Anahtar Kelime / Konu", value="iPhone 15")
    platform_choice = st.selectbox("Platform", options=["reddit", "twitter"])
    limit_slider = st.slider("Analiz Edilecek Yorum Sayısı", min_value=5, max_value=50, value=15, step=5)

    submit_button = st.button("Analizi Başlat", type="primary", use_container_width=True)

# --- Ana Gövde ---
if submit_button:
    with st.spinner("Sosyal medya verileri toplanıyor ve modeller çalıştırılıyor..."):
        data = AnalyticsService.run_analysis(
            query=query_input,
            platform=platform_choice,
            limit=limit_slider
        )

        # Eğer tuple olarak geldiyse ilk elemanı (asıl dict verisini) al
        if isinstance(data, tuple):
            data = data[0]

        if data and isinstance(data, dict) and "metrics" in data:
            metrics = data["metrics"]
            summaries = data["summaries"]
            comments = data["comments"]

            # 1. Satır: Temel Metrik Kartları
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Toplam Yorum", metrics["total_comments"])
            col2.metric("Pozitif Oranı", f"%{metrics['positive_pct']}", delta="Pozitif")
            col3.metric("Negatif Oranı", f"%{metrics['negative_pct']}", delta="-Negatif", delta_color="inverse")
            col4.metric("Nötr Oranı", f"%{metrics['neutral_pct']}")

            st.divider()

            # 2. Satır: Grafik ve Özetler
            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.subheader("🎯 Duygu Dağılımı")
                chart_data = pd.DataFrame({
                    "Duygu": ["Pozitif", "Negatif", "Nötr"],
                    "Oran": [metrics["positive_pct"], metrics["negative_pct"], metrics["neutral_pct"]]
                })

                fig = px.pie(
                    chart_data,
                    names="Duygu",
                    values="Oran",
                    hole=0.45,
                    color="Duygu",
                    color_discrete_map={
                        "Pozitif": "#2ecc71",
                        "Negatif": "#e74c3c",
                        "Nötr": "#95a5a6"
                    }
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

            with right_col:
                st.subheader("🤖 Yapay Zeka Özet Kartları")
                st.success(f"**👍 Öne Çıkan Memnuniyetler:**\n\n{summaries.get('positive_summary', 'Özet yok.')}")
                st.error(f"**👎 Ana Şikayet & Eleştiriler:**\n\n{summaries.get('negative_summary', 'Özet yok.')}")

            st.divider()

            # 3. Satır: Detaylı Yorum Listesi
            st.subheader("💬 Analiz Edilen Yorumlar")
            df_comments = pd.DataFrame(comments)
            if not df_comments.empty:
                df_display = df_comments[["label", "score", "original_text"]].rename(columns={
                    "label": "Duygu",
                    "score": "Güven Skoru",
                    "original_text": "Yorum Metni"
                })
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.error(
                "Backend sunucusundan geçerli veri alınamadı! Lütfen FastAPI sunucusunun (Port 8000) açık olduğundan ve endpoint'in çalıştığından emin olun.")
else:
    st.info("👈 Analizi başlatmak için sol taraftaki menüden parametreleri belirleyip 'Analizi Başlat' butonuna basın.")