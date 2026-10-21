"""
Student percentage distribution pie — how many valid students fall in each
percentage band.
"""

import plotly.graph_objects as go

from exetat_dashboard.config import COLORS, FONT_FAMILY, STUDENT_PERCENTAGE_BUCKETS


def build_distribution_figure(df) -> go.Figure:
    """Build a pie chart from bucket_label and student_count columns."""
    color_by_label = {b["label"]: b["color"] for b in STUDENT_PERCENTAGE_BUCKETS}

    if df is None or df.empty or df["student_count"].sum() == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[{"text": "No data available for this selection", "showarrow": False, "font": {"size": 13, "color": COLORS["muted"], "family": FONT_FAMILY}}],
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    total = int(df["student_count"].sum())
    colors = [color_by_label.get(label, "#CBD5E1") for label in df["bucket_label"]]

    fig = go.Figure(
        go.Pie(
            labels=df["bucket_label"],
            values=df["student_count"],
            sort=False,
            hole=0.64,
            marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2.5)),
            textinfo="percent",
            textfont=dict(color="#FFFFFF", size=11, family=FONT_FAMILY),
            hovertemplate="<b>%{label}</b><br>%{value:,} élèves (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=285,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11, family=FONT_FAMILY, color=COLORS["text_secondary"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family=FONT_FAMILY, color=COLORS["text"]),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=COLORS["primary"], font=dict(color=COLORS["text"], size=13, family=FONT_FAMILY)),
        annotations=[
            dict(
                text=f"<b>{total:,}</b><br><span style='font-size:11px;color:{COLORS['muted']};font-weight:700;letter-spacing:0.06em;'>ÉLÈVES</span>",
                x=0.5, y=0.5, showarrow=False, font=dict(size=24, color=COLORS["text"], family=FONT_FAMILY),
            )
        ],
    )
    return fig
