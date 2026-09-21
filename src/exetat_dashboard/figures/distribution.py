"""
Student percentage distribution pie — how many valid students fall in each
percentage band.
"""

import plotly.graph_objects as go

from exetat_dashboard.config import STUDENT_PERCENTAGE_BUCKETS


def build_distribution_figure(df) -> go.Figure:
    """Build a pie chart from bucket_label and student_count columns."""
    color_by_label = {b["label"]: b["color"] for b in STUDENT_PERCENTAGE_BUCKETS}

    if df is None or df.empty or df["student_count"].sum() == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[{"text": "No data available for this selection", "showarrow": False, "font": {"size": 12, "color": "#7893AA"}}],
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    total = int(df["student_count"].sum())
    colors = [color_by_label.get(label, "#CCCCCC") for label in df["bucket_label"]]

    fig = go.Figure(
        go.Pie(
            labels=df["bucket_label"],
            values=df["student_count"],
            sort=False,
            hole=0.64,
            marker=dict(colors=colors, line=dict(color="#07111F", width=2)),
            textinfo="percent",
            textfont=dict(color="#EDF8FF", size=10),
            hovertemplate="%{label}<br>%{value} student(s) (%{percent})<extra></extra>",
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
            font=dict(size=9, family="Manrope, sans-serif", color="#9BB0C3"),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="Manrope, sans-serif", color="#EDF8FF"),
        hoverlabel=dict(bgcolor="#0C1728", bordercolor="#00A8FF", font=dict(color="#EDF8FF")),
        annotations=[
            dict(
                text=f"<b>{total:,}</b><br><span style='font-size:9px;color:#7893AA'>students</span>",
                x=0.5, y=0.5, showarrow=False, font=dict(size=20),
            )
        ],
    )
    return fig
