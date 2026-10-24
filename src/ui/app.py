"""
Streamlit dashboard.

Çalıştırma:  streamlit run src/ui/app.py
Backend adresi `API_URL` ortam değişkeniyle değiştirilebilir
(varsayılan: http://localhost:8000/api/v1).
"""

import sys
from pathlib import Path

# `streamlit run` yalnızca betiğin klasörünü sys.path'e ekler; `src` paketini bulabilmek için kökü ekle.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from src.models.schemas import Platform  # noqa: E402
from src.ui import charts, components  # noqa: E402
from src.ui.api_client import ApiError, SentimentApiClient  # noqa: E402

st.set_page_config(page_title="Sosyal Medya Duygu Analizi", page_icon="📊", layout="wide")


@st.cache_resource
def get_client() -> SentimentApiClient:
    return SentimentApiClient()


def render_sidebar(client: SentimentApiClient):
    with st.sidebar:
        st.title("📊 Duygu Analizi")
        with st.form("analyze_form"):
            query = st.text_input("Hashtag veya anahtar kelime", value="#iPhone15", max_chars=100)
            platform = st.selectbox(
                "Platform", options=list(Platform),
                format_func=lambda p: {"twitter": "Twitter / X", "reddit": "Reddit", "mock": "Demo (mock)"}[p.value],
            )
            limit = st.slider("Yorum sayısı", min_value=5, max_value=100, value=30, step=5)
            submitted = st.form_submit_button("Analizi başlat", type="primary", width="stretch")

        st.divider()
        try:
            health = client.health()
            st.success(f"Backend bağlı · NLP: {health.nlp_provider}", icon="✅")
            sources = ", ".join(k for k, v in health.sources.items() if v and k != "mock") or "yok (mock modu)"
            st.caption(f"Gerçek API anahtarı olan kaynaklar: {sources}")
        except ApiError as exc:
            st.error(str(exc), icon="🚫")
    return submitted, query.strip(), platform, limit


def render_analysis_tab(client: SentimentApiClient, submitted: bool, query: str, platform: Platform, limit: int):
    if submitted:
        if len(query.lstrip("#")) < 2:
            st.warning("Lütfen en az 2 karakterlik bir sorgu girin.")
        else:
            with st.spinner("Yorumlar toplanıyor ve analiz ediliyor... (ilk çalıştırmada model yüklemesi sürebilir)"):
                try:
                    st.session_state["last_result"] = client.analyze(query, platform, limit)
                except ApiError as exc:
                    st.error(str(exc))

    result = st.session_state.get("last_result")
    if result is None:
        st.info("👈 Soldaki panelden bir hashtag veya anahtar kelime girip **Analizi başlat**'a basın.")
        return
    components.render_result(result, key="current")


def render_history_tab(client: SentimentApiClient):
    search = st.text_input("Geçmişte ara", placeholder="Sorgu metni...", key="history_search")
    try:
        history = client.history(limit=100, query=search or None)
    except ApiError as exc:
        st.error(str(exc))
        return

    if not history.items:
        st.info("Henüz kayıtlı analiz yok.")
        return

    st.caption(f"Toplam {history.total} analiz")
    if len(history.items) >= 2:
        st.plotly_chart(charts.history_trend(history.items, components.current_theme()),
                        width="stretch", key="history_trend")
    st.dataframe(components.history_table(history.items), width="stretch", hide_index=True)

    ids = [item.id for item in history.items]
    labels = {item.id: f"#{item.id} · {item.query} · {item.created_at:%d.%m.%Y %H:%M}" for item in history.items}
    col_select, col_delete = st.columns([4, 1])
    selected_id = col_select.selectbox("Detayını görmek istediğiniz analiz", ids, format_func=labels.get)
    if col_delete.button("🗑️ Sil", width="stretch"):
        try:
            client.delete_analysis(selected_id)
            st.toast(f"#{selected_id} silindi.")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

    try:
        components.render_result(client.get_analysis(selected_id), key=f"history_{selected_id}")
    except ApiError as exc:
        st.error(str(exc))


def main() -> None:
    client = get_client()
    submitted, query, platform, limit = render_sidebar(client)
    tab_analysis, tab_history = st.tabs(["🔍 Yeni analiz", "🕘 Geçmiş"])
    with tab_analysis:
        render_analysis_tab(client, submitted, query, platform, limit)
    with tab_history:
        render_history_tab(client)


main()
