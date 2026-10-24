"""
Plotly grafik fabrikaları (saf fonksiyonlar; Streamlit bağımlılığı yok).

Renkler duygu kutuplarını (diverging) kodlar: olumlu=mavi, olumsuz=kırmızı,
nötr=gri. Renk körlüğü ayrımı doğrulanmıştır; kimlik yine de hiçbir zaman
yalnızca renge bırakılmaz (doğrudan etiketler + lejant).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.models.schemas import CommentResult, HistoryItem, SentimentDistribution

LABELS_TR = {"positive": "Olumlu", "negative": "Olumsuz", "neutral": "Nötr"}
_ORDER = ["Olumlu", "Nötr", "Olumsuz"]

_PALETTES = {
    "light": {"Olumlu": "#2a78d6", "Olumsuz": "#e34948", "Nötr": "#8a8984", "grid": "#e4e3df"},
    "dark": {"Olumlu": "#3987e5", "Olumsuz": "#e66767", "Nötr": "#b5b3ad", "grid": "#2e2e2c"},
}


def palette(theme: str) -> dict[str, str]:
    return _PALETTES.get(theme, _PALETTES["light"])


def _base_layout(fig: go.Figure, theme: str, height: int = 340) -> go.Figure:
    grid = palette(theme)["grid"]
    fig.update_layout(
        height=height,
        margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(gridcolor=grid, zeroline=False)
    fig.update_yaxes(gridcolor=grid, zeroline=False)
    return fig


def distribution_donut(dist: SentimentDistribution, theme: str) -> go.Figure:
    colors = palette(theme)
    counts = {"Olumlu": dist.positive, "Nötr": dist.neutral, "Olumsuz": dist.negative}
    fig = go.Figure(go.Pie(
        labels=list(counts),
        values=list(counts.values()),
        hole=0.6,
        sort=False,
        marker=dict(colors=[colors[k] for k in counts], line=dict(color="rgba(0,0,0,0)", width=2)),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} yorum (%{percent})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{dist.total}</b><br>yorum", showarrow=False, font_size=16)
    return _base_layout(fig, theme)


def confidence_histogram(comments: list[CommentResult], theme: str) -> go.Figure:
    df = pd.DataFrame({
        "Duygu": [LABELS_TR[c.label.value] for c in comments],
        "Güven": [c.score for c in comments],
    })
    fig = px.histogram(
        df, x="Güven", color="Duygu", nbins=10, barmode="group",
        category_orders={"Duygu": _ORDER}, color_discrete_map=palette(theme),
        labels={"Güven": "Model güven skoru", "count": "Yorum"},
    )
    fig.update_traces(marker_line_width=2, marker_line_color="rgba(0,0,0,0)",
                      hovertemplate="Güven %{x}: %{y} yorum<extra></extra>")
    fig.update_layout(bargap=0.15, yaxis_title="Yorum sayısı")
    return _base_layout(fig, theme)


def sentiment_timeline(comments: list[CommentResult], theme: str) -> go.Figure | None:
    """Yorumların zamana göre duygu dağılımı; tarih bilgisi yoksa None döner."""
    rows = [(c.created_at, LABELS_TR[c.label.value]) for c in comments if c.created_at]
    if len(rows) < 3:
        return None
    df = pd.DataFrame(rows, columns=["Zaman", "Duygu"])
    span_hours = (df["Zaman"].max() - df["Zaman"].min()).total_seconds() / 3600
    df["Dönem"] = df["Zaman"].dt.floor("D" if span_hours > 48 else "h")
    grouped = df.groupby(["Dönem", "Duygu"]).size().reset_index(name="Yorum")
    fig = px.bar(
        grouped, x="Dönem", y="Yorum", color="Duygu",
        category_orders={"Duygu": _ORDER}, color_discrete_map=palette(theme),
    )
    fig.update_traces(marker_line_width=1, marker_line_color="rgba(0,0,0,0)",
                      hovertemplate="%{x}<br>%{y} yorum<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Yorum sayısı", bargap=0.2)
    return _base_layout(fig, theme)


def history_trend(items: list[HistoryItem], theme: str) -> go.Figure:
    """Geçmiş analizlerde olumlu/olumsuz oranın zaman içindeki seyri."""
    df = pd.DataFrame([
        {"Tarih": i.created_at, "Sorgu": i.query, "Olumlu": i.positive_pct, "Olumsuz": i.negative_pct}
        for i in items
    ]).sort_values("Tarih")
    long = df.melt(id_vars=["Tarih", "Sorgu"], value_vars=["Olumlu", "Olumsuz"],
                   var_name="Duygu", value_name="Oran")
    fig = px.line(
        long, x="Tarih", y="Oran", color="Duygu", markers=True, hover_data=["Sorgu"],
        color_discrete_map=palette(theme),
    )
    fig.update_traces(line_width=2, marker_size=8)
    fig.update_layout(xaxis_title=None, yaxis_title="Oran (%)", yaxis_range=[0, 100], hovermode="x unified")
    return _base_layout(fig, theme, height=300)
