"""Dashboard'un yeniden kullanılabilir Streamlit bileşenleri."""

import pandas as pd
import streamlit as st

from src.models.schemas import AnalysisResult, HistoryItem
from src.ui import charts
from src.ui.charts import LABELS_TR

_PLATFORM_NAMES = {"twitter": "Twitter / X", "reddit": "Reddit", "mock": "Demo (mock)"}


def current_theme() -> str:
    """Streamlit temasını ('light' / 'dark') döndürür; eski sürümlerde 'light' varsayar."""
    try:
        return st.context.theme.type or "light"
    except AttributeError:
        return "light"


def render_metrics(result: AnalysisResult) -> None:
    dist = result.distribution
    cols = st.columns(4)
    cols[0].metric("Toplam yorum", dist.total)
    cols[1].metric("Olumlu", f"%{dist.positive_pct:g}", f"{dist.positive} yorum", delta_color="off")
    cols[2].metric("Olumsuz", f"%{dist.negative_pct:g}", f"{dist.negative} yorum", delta_color="off")
    cols[3].metric("Nötr", f"%{dist.neutral_pct:g}", f"{dist.neutral} yorum", delta_color="off")


def render_source_info(result: AnalysisResult) -> None:
    platform = _PLATFORM_NAMES.get(result.platform.value, result.platform.value)
    created = result.created_at.strftime("%d.%m.%Y %H:%M")
    st.caption(f"Kaynak: **{platform}** · NLP: **{result.nlp_provider}** · {created} UTC"
               + (f" · Kayıt #{result.id}" if result.id else ""))
    if result.is_mock_data:
        st.warning(
            "Bu sonuçlar **mock (demo) veri** ile üretildi. Gerçek veri için `.env` dosyasına "
            "ilgili platformun API anahtarlarını ekleyin.",
            icon="⚠️",
        )


def render_summary(result: AnalysisResult) -> None:
    st.subheader("🤖 Yapay zeka özeti")
    with st.container(border=True):
        st.markdown(result.summary.overview)
    left, right = st.columns(2)
    with left:
        st.markdown("**👍 Öne çıkan övgüler**")
        st.info(result.summary.positive_highlights or "—")
    with right:
        st.markdown("**👎 Öne çıkan şikayetler**")
        st.error(result.summary.negative_highlights or "—")


def render_charts(result: AnalysisResult, theme: str, key: str) -> None:
    left, right = st.columns(2)
    with left:
        st.subheader("Duygu dağılımı")
        st.plotly_chart(charts.distribution_donut(result.distribution, theme),
                        width="stretch", key=f"donut_{key}")
    with right:
        st.subheader("Model güven dağılımı")
        st.plotly_chart(charts.confidence_histogram(result.comments, theme),
                        width="stretch", key=f"confidence_{key}")

    timeline = charts.sentiment_timeline(result.comments, theme)
    if timeline is not None:
        st.subheader("Zamana göre duygu")
        st.plotly_chart(timeline, width="stretch", key=f"timeline_{key}")


def render_comments(result: AnalysisResult, key: str) -> None:
    st.subheader("💬 Yorumlar")
    options = list(LABELS_TR.values())
    selected = st.multiselect("Duyguya göre filtrele", options, default=options, key=f"filter_{key}")

    df = pd.DataFrame([
        {
            "Duygu": LABELS_TR[c.label.value],
            "Güven": c.score,
            "Dil": c.language,
            "Yazar": c.author or "",
            "Yorum": c.original_text,
        }
        for c in result.comments
    ])
    if df.empty:
        st.info("Gösterilecek yorum yok.")
        return
    st.dataframe(
        df[df["Duygu"].isin(selected)],
        width="stretch",
        hide_index=True,
        column_config={
            "Güven": st.column_config.ProgressColumn("Güven", min_value=0.0, max_value=1.0, format="%.2f"),
            "Yorum": st.column_config.TextColumn("Yorum", width="large"),
        },
    )


def render_result(result: AnalysisResult, key: str) -> None:
    """Bir analiz sonucunun tam görünümü."""
    theme = current_theme()
    st.header(f"“{result.query}” analizi")
    render_source_info(result)
    render_metrics(result)
    st.divider()
    render_summary(result)
    st.divider()
    render_charts(result, theme, key)
    st.divider()
    render_comments(result, key)


def _platform_label(item: HistoryItem) -> str:
    name = _PLATFORM_NAMES.get(item.platform.value, item.platform.value)
    fell_back_to_mock = item.is_mock_data and item.platform.value != "mock"
    return f"{name} (mock)" if fell_back_to_mock else name


def history_table(items: list[HistoryItem]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ID": i.id,
            "Tarih": i.created_at.strftime("%d.%m.%Y %H:%M"),
            "Sorgu": i.query,
            "Platform": _platform_label(i),
            "Yorum": i.total_comments,
            "Olumlu %": i.positive_pct,
            "Olumsuz %": i.negative_pct,
            "Nötr %": i.neutral_pct,
            "Baskın": LABELS_TR[i.dominant_sentiment.value],
        }
        for i in items
    ])
