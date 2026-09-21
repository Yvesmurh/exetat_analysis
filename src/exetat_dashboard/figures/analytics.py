"""Shared detail-page presentation built from the existing theme and KPI cards."""
import pandas as pd
import plotly.graph_objects as go
from dash import html
from exetat_dashboard.config import COLORS
from exetat_dashboard.figures.overview_cards import (
    _kpi_card, _fmt_int, _ICON_SCHOOL, _ICON_USERS, _ICON_CHECK, _ICON_TARGET,
)
from exetat_dashboard.queries.analytics import BAND_LABELS, TREND_YEARS

EMPTY_MESSAGE = "No data available for this selection."


def empty_state(message=EMPTY_MESSAGE):
    return html.Div(message, className="empty-state", role="status")


def percentage(value):
    return "—" if value is None or pd.isna(value) else f"{float(value):.2f}%"


def change_badge(value, suffix=""):
    if value is None or pd.isna(value):
        return html.Span("No previous-year data", className="delta-badge delta-neutral")
    value = round(float(value), 2)
    direction, css = ("↑", "delta-up") if value > 0 else (("↓", "delta-down") if value < 0 else ("→", "delta-neutral"))
    return html.Span(f"{direction} {value:+.2f} pts{suffix}", className=f"delta-badge {css}")


def build_scope_overview(data, year, school=False):
    if not data:
        return empty_state()
    previous = data.get("previous_success_rate")
    rate = data.get("success_rate")
    comparison = [html.Div(f"{year} · Current year", className="analytics-kpi-note")]
    if previous is None:
        comparison.append(change_badge(None))
    else:
        comparison.append(html.Div(f"{int(year) - 1}: {percentage(previous)}", className="analytics-kpi-note"))
        if rate is not None:
            comparison.append(change_badge(data.get("success_rate_delta_vs_prev_year"), f" vs {int(year) - 1}"))
    if rate is None:
        comparison.append(html.Div("Rate unavailable for this selection", className="analytics-kpi-note"))
    return html.Div([
        _kpi_card("Total Options" if school else "Total Schools",
                  _fmt_int(data.get("total_options" if school else "total_schools")), icon=_ICON_SCHOOL),
        _kpi_card("Total Participants", _fmt_int(data.get("total_participants")), icon=_ICON_USERS),
        _kpi_card("Total Successful Students", _fmt_int(data.get("total_successful")), icon=_ICON_CHECK),
        _kpi_card("School Success Rate" if school else "Province Success Rate", percentage(rate),
                  icon=_ICON_TARGET, extra=html.Div(comparison, className="analytics-comparison")),
    ], className="kpi-row analytics-kpis")


def _table(headers, rows):
    return html.Div(html.Table([
        html.Thead(html.Tr([html.Th(title, scope="col") for title in headers])),
        html.Tbody(rows),
    ], className="analytics-table"), className="analytics-table-scroll", tabIndex=0)


def build_option_leaders(df, year):
    if df is None or df.empty:
        return empty_state()
    rows = [html.Tr([
        html.Td(row.option_name), html.Td(row.top_student_current),
        html.Td(percentage(row.top_percentage_current), className="analytics-score"),
        html.Td(percentage(row.top_percentage_previous)), html.Td(change_badge(row.pts_change)),
    ]) for row in df.itertuples()]
    return _table(["Option", "Student", f"{year} score", f"{int(year) - 1} best", "Change (pts)"], rows)


def build_detail_ranking(df, school=False):
    if df is None or df.empty:
        return empty_state()
    rows = []
    for row in df.itertuples():
        values = [html.Span(str(row.rank), className="ranking-rank")]
        if school:
            values += [row.student_name, row.option_name or "—", percentage(row.percentage)]
        else:
            values += [row.school_name, _fmt_int(row.participants), _fmt_int(row.successes), percentage(row.success_rate)]
        rows.append(html.Tr([html.Td(value, className="analytics-score" if i == len(values)-1 else "")
                             for i, value in enumerate(values)]))
    headers = (["Rank", "Student", "Option", "Percentage"] if school else
               ["Rank", "School", "Participants", "Successful", "Success Rate"])
    return _table(headers, rows)


def _base_figure():
    fig = go.Figure()
    fig.update_layout(
        autosize=True, height=310, margin=dict(l=55, r=25, t=20, b=45),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", size=11, color=COLORS["text"]),
        hoverlabel=dict(bgcolor=COLORS["card_bg"], bordercolor=COLORS["primary"], font=dict(color=COLORS["text"])),
        showlegend=False,
    )
    return fig


def empty_figure(message=EMPTY_MESSAGE):
    fig = _base_figure()
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False),
                      annotations=[dict(text=message, x=.5, y=.5, xref="paper", yref="paper",
                                        showarrow=False, font=dict(color=COLORS["muted"], size=12))])
    return fig


def build_scope_trend(df):
    if df is None or df.empty or df["success_rate"].isna().all():
        return empty_figure()
    series = pd.to_numeric(df.set_index("year")["success_rate"], errors="coerce").reindex(TREND_YEARS)
    fig = _base_figure()
    fig.add_trace(go.Scatter(
        x=TREND_YEARS, y=[None if pd.isna(v) else float(v) for v in series],
        mode="lines+markers", connectgaps=False,
        line=dict(color=COLORS["primary_dark"], width=3),
        marker=dict(size=7, color=COLORS["primary_dark"]),
        hovertemplate="Year %{x}<br>Success rate: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(title="Year", dtick=1, range=[2014.75, 2023.25], showgrid=False,
                   tickfont=dict(color=COLORS["muted"])),
        yaxis=dict(title="Success Rate (%)", ticksuffix="%", rangemode="tozero",
                   gridcolor=COLORS["border"], zeroline=False, tickfont=dict(color=COLORS["muted"])),
        hovermode="x unified",
    )
    return fig


def build_range_distribution(df, school=False):
    if df is None or df.empty or df["item_count"].sum() == 0:
        return empty_figure()
    counts = df.set_index("bucket_label")["item_count"].reindex(BAND_LABELS, fill_value=0)
    unit = "students" if school else "schools"
    fig = _base_figure()
    fig.add_trace(go.Bar(
        y=BAND_LABELS, x=[int(v) for v in counts], orientation="h",
        marker_color=[COLORS["primary_dark"], COLORS["primary"], "#0284C7", "#075985", "#FFC857", COLORS["danger"]],
        text=[f"{int(v):,}" for v in counts], textposition="outside", cliponaxis=False,
        hovertemplate=f"%{{y}}<br>%{{x:,}} {unit}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=88, r=48, t=20, b=45), bargap=.35,
        xaxis=dict(title=f"Number of {unit}", rangemode="tozero", gridcolor=COLORS["border"],
                   tickformat=",d", range=[0, max(1, float(counts.max()) * 1.2)]),
        yaxis=dict(autorange="reversed", showgrid=False),
    )
    return fig
