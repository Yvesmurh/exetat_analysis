"""
Home page — Exetat National Results Dashboard.

Sections: global filters (year / province / educational option), national
overview KPI cards, top performing students per option, province
performance trend, DRC province choropleth map + dynamic legend, success
rate distribution, and province ranking (top 5 with a "show all" toggle).

Layout follows a 3-column dashboard grid (see assets/style.css
`.dashboard-grid`):

    1. National Overview    |                          | 5. Province Ranking
    2. Top Students         |  4. Province Map          | 6. Success Rate by Range
    3. Province Performance Trend (full width)
"""

import dash
import pandas as pd
from dash import Input, Output, State, dcc, html

from exetat_dashboard.config import (
    AVAILABLE_YEARS,
    DEFAULT_OPTION,
    DEFAULT_YEAR,
    MAP_COLORSCALE,
    OPTIONS_LIST,
    PROVINCES_26,
    SUCCESS_RATE_BUCKETS,
)
from exetat_dashboard.figures.distribution import build_distribution_figure
from exetat_dashboard.figures.map import create_choropleth
from exetat_dashboard.figures.overview_cards import build_overview_cards, build_top_students_table, top_students_toggle_label
from exetat_dashboard.figures.ranking import build_ranking_table, toggle_button_label
from exetat_dashboard.figures.trend import build_trend_cards
from exetat_dashboard.queries.overview import get_national_overview, get_top_students_by_option
from exetat_dashboard.queries.province import get_province_stats, get_student_percentage_distribution
from exetat_dashboard.queries.trends import get_province_trends

dash.register_page(__name__, path="/", name="Home")

ALL_PROVINCES_LABEL = "Toutes les provinces"
TREND_YEARS = [2018, 2019, 2020, 2021, 2022, 2023]

MAP_HOVER_COLS = ["schools", "participants", "delta_vs_prev_year"]
MAP_HOVER_LABELS = {
    "schools": "Schools",
    "participants": "Participants",
    "delta_vs_prev_year": "YoY change (pts)",
}


def _clean(value: str | None, all_label: str) -> str | None:
    """Normalize a dropdown's 'all' sentinel to None for the query layer."""
    return None if value in (None, "", all_label) else value


def _bucket_provinces_from_df(df: pd.DataFrame, rate_col: str = "success_rate") -> pd.DataFrame:
    """Count provinces per SUCCESS_RATE_BUCKETS band from an
    already-fetched province-level dataframe (fraction 0-1 scale, same as
    SUCCESS_RATE_BUCKETS' min/max). Used for the map legend only — the
    distribution donut now queries get_success_rate_distribution() directly."""
    labels = [b["label"] for b in SUCCESS_RATE_BUCKETS]
    counts = {label: 0 for label in labels}
    if df is not None and not df.empty and rate_col in df:
        for rate in df[rate_col].dropna():
            for bucket in SUCCESS_RATE_BUCKETS:
                if bucket["min"] <= rate < bucket["max"]:
                    counts[bucket["label"]] += 1
                    break
    return pd.DataFrame({"bucket_label": labels, "province_count": [counts[label] for label in labels]})


def _build_map_legend(df: pd.DataFrame, rate_col: str = "success_rate") -> html.Div:
    """Simple bucketed legend under the map: how many provinces fall in
    each success-rate band, colored to match SUCCESS_RATE_BUCKETS. Built
    inline here since the new map.py module only returns the figure."""
    bucket_df = _bucket_provinces_from_df(df, rate_col=rate_col)
    counts_by_label = dict(zip(bucket_df["bucket_label"], bucket_df["province_count"]))
    items = []
    for bucket in SUCCESS_RATE_BUCKETS:
        items.append(
            html.Div(
                [
                    html.Span(className="legend-swatch", style={"backgroundColor": bucket.get("color", "#ccc")}),
                    html.Span(f"{bucket['label']}: {counts_by_label.get(bucket['label'], 0)} provinces"),
                ],
                className="legend-item",
            )
        )
    return html.Div(items, className="map-legend")


def _filters_row() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Label("Year", className="filter-label"),
                    dcc.Dropdown(
                        id="year-dropdown",
                        options=[{"label": str(y), "value": y} for y in AVAILABLE_YEARS],
                        value=DEFAULT_YEAR if DEFAULT_YEAR in AVAILABLE_YEARS else (AVAILABLE_YEARS[-1] if AVAILABLE_YEARS else None),
                        clearable=False,
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label("Province", className="filter-label"),
                    dcc.Dropdown(
                        id="province-dropdown",
                        options=[{"label": ALL_PROVINCES_LABEL, "value": ALL_PROVINCES_LABEL}]
                        + [{"label": p.title(), "value": p} for p in PROVINCES_26],
                        value=ALL_PROVINCES_LABEL,
                        clearable=False,
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label("Educational Option", className="filter-label"),
                    dcc.Dropdown(
                        id="option-dropdown",
                        options=[{"label": o, "value": o} for o in OPTIONS_LIST],
                        value=DEFAULT_OPTION,
                        clearable=False,
                    ),
                ],
                className="filter-item",
            ),
            html.Button("Apply Filters", id="apply-filters-btn", n_clicks=0, className="apply-filters-btn"),
        ],
        className="filters-row",
    )


def _header() -> html.Div:
    brand_icon = html.Img(
        src=(
            "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' "
            "fill='none' stroke='%23007FFF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M22 10 12 4 2 10l10 6 10-6Z'/><path d='M6 12v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5'/>"
            "<path d='M22 10v6'/></svg>"
        ),
        alt="Education icon",
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Div(brand_icon, className="header-brand-icon"),
                    html.Div(
                        [
                            html.Div("NATIONAL EDUCATION ANALYTICS", className="eyebrow"),
                            html.H1("Exetat Performance Intelligence", className="page-title"),
                            html.P("National examination outcomes, provincial signals and education performance", className="page-subtitle"),
                        ],
                        className="header-titles",
                    ),
                ],
                className="header-brand",
            ),
            html.Div(
                [
                    html.Div([html.Span("ACTIVE DATASET"), html.Strong(id="active-year-label")], className="active-dataset"),
                    _filters_row(),
                ],
                className="header-controls",
            ),
        ],
        className="dashboard-header",
    )


def _card(number: str, title: str, subtitle: str, body, extra_class: str = "") -> html.Div:
    header_children = [
        html.H2([html.Span(f"0{number}", className="section-number"), html.Span(title)], className="card-title"),
    ]
    if subtitle:
        header_children.append(html.P(subtitle, className="card-subtitle"))
    return html.Div(
        [html.Div(header_children, className="card-header"), body],
        className=f"dash-card {extra_class}".strip(),
    )

layout = html.Div(
    [
        _header(),

        html.Div(
            [
                # LEFT COLUMN: National Overview + Top Performing Students, stacked
                html.Div(
                    [
                        _card(
                            "1",
                            "National Overview",
                            "Schools, participants & success rate",
                            html.Div(id="overview-cards"),
                        ),
                        _card(
                            "2",
                            "Top Performing Students",
                            "Best score per educational option",
                            html.Div(
                                [
                                    html.Div(id="top-students-container"),
                                    html.Button(
                                        "Show all students ▾",
                                        id="students-toggle-btn",
                                        n_clicks=0,
                                        className="ranking-toggle-btn",
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                        ),
                    ],
                    className="area-left",
                ),

                # MIDDLE COLUMN: Province Performance Map
                html.Div(
                    _card(
                        "4",
                        "Province Performance Map",
                        "Success rate by province, vs. prior year",
                        html.Div(
                            [
                                dcc.Graph(
                                    id="province-map",
                                    config={"displayModeBar": False, "responsive": True},
                                    className="map-graph",
                                    style={"width": "100%", "height": "100%"},
                                ),
                                html.Div(id="map-legend"),
                            ],
                            className="map-row",
                        ),
                        extra_class="dash-card--map",
                    ),
                    className="area-map",
                ),

                # RIGHT COLUMN: Province Ranking + Success Rate by Range, stacked
                html.Div(
                    [
                        _card(
                            "5",
                            "Province Ranking",
                            "By Success Rate",
                            html.Div(
                                [
                                    html.Div(id="ranking-table-container"),
                                    html.Button(
                                        "Show all provinces ▾",
                                        id="ranking-toggle-btn",
                                        n_clicks=0,
                                        className="ranking-toggle-btn",
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                        ),
                        _card(
                            "6",
                            "Student Percentage by Range",
                            "Students per percentage band",
                            dcc.Graph(id="distribution-graph", config={"displayModeBar": False}),
                        ),
                    ],
                    className="area-right",
                ),

                # FULL-WIDTH: Province Performance Trend
                html.Div(
                    _card(
                        "3",
                        "Province Performance Trend",
                        "Success rate (%) by province — select a province to highlight it",
                        html.Div(id="trend-cards-container"),
                    ),
                    className="area-trend",
                ),
            ],
            className="dashboard-grid",
        ),

        dcc.Store(id="province-stats-store"),
        dcc.Store(id="ranking-show-all-store", data=False),
        dcc.Store(id="students-show-all-store", data=False),
    ],
    className="home-page",
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@dash.callback(
    Output("province-stats-store", "data"),
    Input("year-dropdown", "value"),
    Input("option-dropdown", "value"),
    Input("apply-filters-btn", "n_clicks"),
)
def _update_province_stats(year, option, _n_clicks):
    """Single query shared by the ranking and distribution donut — avoids
    re-running get_province_stats() twice per filter change.
    Intentionally NOT filtered by province: these components are
    inherently province-to-province comparisons. `apply-filters-btn` is
    included only so the visible "Apply Filters" button re-fires this
    callback with the filters' current values; the dropdowns already
    trigger it live, so clicking it is a harmless no-op re-render."""
    if year is None:
        return []
    df = get_province_stats(year, option)
    if df is None or df.empty:
        return []
    df = df.where(pd.notnull(df), None)
    return df.to_dict("records")


@dash.callback(Output("active-year-label", "children"), Input("year-dropdown", "value"))
def _render_active_year(year):
    return str(year) if year is not None else "—"


@dash.callback(
    Output("overview-cards", "children"),
    Input("year-dropdown", "value"),
    Input("province-dropdown", "value"),
    Input("option-dropdown", "value"),
    Input("apply-filters-btn", "n_clicks"),
)
def _render_overview_cards(year, province, option, _n_clicks):
    if year is None:
        return build_overview_cards({})
    overview = get_national_overview(year, option, _clean(province, ALL_PROVINCES_LABEL))
    return build_overview_cards(overview)


@dash.callback(
    Output("students-show-all-store", "data"),
    Input("students-toggle-btn", "n_clicks"),
    State("students-show-all-store", "data"),
    prevent_initial_call=True,
)
def _toggle_students(n_clicks, show_all):
    return not show_all


@dash.callback(
    Output("top-students-container", "children"),
    Output("students-toggle-btn", "children"),
    Output("students-toggle-btn", "style"),
    Input("year-dropdown", "value"),
    Input("province-dropdown", "value"),
    Input("option-dropdown", "value"),
    Input("apply-filters-btn", "n_clicks"),
    Input("students-show-all-store", "data"),
)
def _render_top_students(year, province, option, _n_clicks, show_all):
    if year is None:
        return build_top_students_table(pd.DataFrame()), "", {"display": "none"}
    df = get_top_students_by_option(year, option, _clean(province, ALL_PROVINCES_LABEL))
    table = build_top_students_table(df, show_all=show_all)
    label = top_students_toggle_label(len(df), show_all)
    style = {"display": "inline-block"} if label else {"display": "none"}
    return table, label, style


@dash.callback(
    Output("trend-cards-container", "children"),
    Input("option-dropdown", "value"),
    Input("province-dropdown", "value"),
    Input("apply-filters-btn", "n_clicks"),
)
def _render_trend(option, province, _n_clicks):
    df = get_province_trends(PROVINCES_26, TREND_YEARS, option)
    highlight = _clean(province, ALL_PROVINCES_LABEL)
    return build_trend_cards(df, highlight_province=highlight)


@dash.callback(
    Output("province-map", "figure"),
    Input("province-stats-store", "data"),
    Input("province-dropdown", "value"),
)
def _render_map(records, province):
    df = pd.DataFrame(records) if records else pd.DataFrame()
    selected = _clean(province, ALL_PROVINCES_LABEL)

    if df.empty:
        fig = create_choropleth(
            pd.DataFrame({"province": [], "success_rate_pct": []}),
            location_col="province",
            value_col="success_rate_pct",
            colorscale=MAP_COLORSCALE,
        )
    else:
        # success_rate arrives as a 0-1 fraction (matches SUCCESS_RATE_BUCKETS);
        # scale to a percentage just for the map's color/hover display.
        df = df.assign(success_rate_pct=df["success_rate"] * 100)
        fig = create_choropleth(
            df,
            location_col="province",
            value_col="success_rate_pct",
            hover_name_col="province",
            hover_cols=MAP_HOVER_COLS,
            hover_labels=MAP_HOVER_LABELS,
            colorbar_title="Success rate (%)",
            colorscale=MAP_COLORSCALE,
            selected_location=selected,
        )

    return fig


@dash.callback(
    Output("distribution-graph", "figure"),
    Input("year-dropdown", "value"),
    Input("option-dropdown", "value"),
    Input("apply-filters-btn", "n_clicks"),
)
def _render_distribution(year, option, _n_clicks):
    if year is None:
        return build_distribution_figure(pd.DataFrame(columns=["bucket_label", "province_count"]))
    df = get_student_percentage_distribution(year, option)
    return build_distribution_figure(df)


@dash.callback(
    Output("ranking-show-all-store", "data"),
    Input("ranking-toggle-btn", "n_clicks"),
    State("ranking-show-all-store", "data"),
    prevent_initial_call=True,
)
def _toggle_ranking(n_clicks, show_all):
    return not show_all


@dash.callback(
    Output("ranking-table-container", "children"),
    Output("ranking-toggle-btn", "children"),
    Output("ranking-toggle-btn", "style"),
    Input("province-stats-store", "data"),
    Input("ranking-show-all-store", "data"),
)
def _render_ranking(records, show_all):
    df = pd.DataFrame(records) if records else pd.DataFrame()
    table = build_ranking_table(df, show_all=show_all)
    label = toggle_button_label(len(df), show_all)
    style = {"display": "inline-block"} if label else {"display": "none"}
    return table, label, style
