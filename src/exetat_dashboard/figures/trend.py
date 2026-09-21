"""
Province performance trend — one card + one figure per province, success
rate over time (small multiples), plus a flat pivot table.

`build_trend_cards()` is what home.py's "3. Province Performance Trend"
section renders: a responsive grid (see assets/style.css
`.province-trend-grid`) of per-province cards, each with its own bigger
line/area chart, a current-rate readout, and a delta badge. Selecting a
province (`highlight_province`) pins its card first and gives it the
`.province-trend-card--selected` treatment.
"""

import re

import plotly.graph_objects as go
from dash import dash_table, dcc, html

from exetat_dashboard.config import COLORS


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """'#5B35D5' -> 'rgba(91,53,213,0.12)'. Falls back to a flat grey if
    hex_color isn't a plain #rrggbb string (e.g. it's already an rgba())."""
    match = re.fullmatch(r"#?([0-9A-Fa-f]{6})", hex_color or "")
    if not match:
        return f"rgba(107,114,128,{alpha})"
    r, g, b = (int(match.group(1)[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _province_card_figure(prov_df, highlighted: bool) -> go.Figure:
    """Single-series line+area chart for one province, sized for the
    bigger per-card layout (see .province-trend-graph, height: 320px)."""
    color = COLORS["primary_dark"] if highlighted else COLORS["primary"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=prov_df["year"],
            y=prov_df["success_rate"] * 100,
            mode="lines+markers",
            line=dict(width=2.75, color=color, shape="spline", smoothing=0.25),
            marker=dict(size=5, color=color, line=dict(width=1, color="#07111F")),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.12),
            hovertemplate="Year %{x}<br>Success rate: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=38, r=12, t=6, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=150,
        font=dict(family="Manrope, sans-serif", color=COLORS["text"], size=9),
        xaxis=dict(
            dtick=1,
            showgrid=False,
            showline=True,
            linecolor=COLORS["border"],
            tickfont=dict(size=8, color=COLORS["muted"]),
        ),
        yaxis=dict(
            ticksuffix="%",
            showgrid=True,
            gridcolor=COLORS["border"],
            zeroline=False,
            rangemode="tozero",
            tickfont=dict(size=8, color=COLORS["muted"]),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0C1728", bordercolor=COLORS["primary"], font=dict(family="Manrope, sans-serif", color=COLORS["text"])),
        showlegend=False,
    )
    return fig


def build_trend_cards(df, highlight_province: str | None = None) -> html.Div:
    """df: pandas.DataFrame from queries.trends.get_province_trends()
    with columns province, year, success_rate (0-1).

    Renders one card per province into `.province-trend-grid`. The
    highlighted province (if any) is sorted to the front and rendered
    with the `--selected` card style; every card gets its own bigger
    figure rather than all provinces sharing a single combined chart."""
    if df is None or df.empty:
        return html.Div("No trend data available for this selection.", className="empty-state")

    provinces = sorted(df["province"].unique())
    if highlight_province in provinces:
        provinces = [highlight_province] + [p for p in provinces if p != highlight_province]

    cards = []
    for province in provinces:
        prov_df = df[df["province"] == province].sort_values("year")
        if prov_df.empty:
            continue

        series = prov_df["success_rate"].dropna()
        current = series.iloc[-1] * 100 if not series.empty else None
        is_highlighted = highlight_province is not None and province == highlight_province

        if len(series) >= 2:
            delta = (series.iloc[-1] - series.iloc[0]) * 100
            if delta > 0.05:
                delta_class, arrow = "delta-up", "↗"
            elif delta < -0.05:
                delta_class, arrow = "delta-down", "↘"
            else:
                delta_class, arrow = "delta-neutral", "→"
            delta_text = f"{arrow} {delta:+.1f} pts since {int(prov_df['year'].iloc[0])}"
        else:
            delta_class, delta_text = "delta-neutral", "Not enough data for a trend"

        card = html.Div(
            [
                html.Div(
                    [
                        html.H3(province.title(), className="province-trend-title"),
                        html.Span(
                            f"{current:.1f}%" if current is not None else "—",
                            className="province-trend-rate",
                        ),
                    ],
                    className="province-trend-heading",
                ),
                html.P(delta_text, className=f"province-trend-delta {delta_class}"),
                dcc.Graph(
                    figure=_province_card_figure(prov_df, is_highlighted),
                    config={"displayModeBar": False},
                    className="province-trend-graph",
                ),
            ],
            className="province-trend-card" + (" province-trend-card--selected" if is_highlighted else ""),
        )
        cards.append(card)

    return html.Div(cards, className="province-trend-grid")


def build_trend_table(df) -> html.Div:
    """df: pandas.DataFrame from queries.trends.get_province_trends()
    with columns province, year, success_rate (0-1). Pivots to one row per
    province, one column per year, plus a simple up/down trend arrow
    comparing the first and last available year."""
    if df is None or df.empty:
        return html.Div("No trend data available for this selection.", className="empty-state")

    pivot = df.pivot_table(index="province", columns="year", values="success_rate", aggfunc="mean")
    years = sorted(pivot.columns.tolist())
    pivot = pivot.reindex(columns=years)

    records = []
    for province, row in pivot.iterrows():
        record = {"province": str(province).title()}
        series = row.dropna()
        for year in years:
            val = row.get(year)
            record[str(year)] = f"{val * 100:.1f}%" if val == val else "—"
        if len(series) >= 2:
            delta = series.iloc[-1] - series.iloc[0]
            record["trend"] = "↗" if delta > 0 else ("↘" if delta < 0 else "→")
        else:
            record["trend"] = "—"
        records.append(record)

    columns = [{"name": "Province", "id": "province"}]
    columns += [{"name": str(y), "id": str(y)} for y in years]
    columns.append({"name": "Trend", "id": "trend"})

    return html.Div(
        dash_table.DataTable(
            id="trend-table",
            columns=columns,
            data=records,
            style_as_list_view=True,
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": COLORS["primary_light"],
                "color": COLORS["primary_dark"],
                "fontWeight": "600",
                "border": "none",
                "fontSize": "12px",
                "whiteSpace": "nowrap",
            },
            style_cell={
                "backgroundColor": COLORS["card_bg"],
                "color": COLORS["text"],
                "padding": "8px 12px",
                "fontFamily": "inherit",
                "fontSize": "12px",
                "border": "none",
                "borderBottom": f"1px solid {COLORS['border']}",
                "whiteSpace": "nowrap",
            },
            style_cell_conditional=[{"if": {"column_id": "province"}, "textAlign": "left", "fontWeight": "600"}],
            style_data_conditional=[
                {"if": {"column_id": "trend", "filter_query": "{trend} = '↗'"}, "color": COLORS["success"], "fontWeight": "700"},
                {"if": {"column_id": "trend", "filter_query": "{trend} = '↘'"}, "color": COLORS["danger"], "fontWeight": "700"},
            ],
        ),
        className="trend-table-wrap",
    )
