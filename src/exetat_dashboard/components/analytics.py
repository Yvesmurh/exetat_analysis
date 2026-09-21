"""Shared detail-page shell, preserving the Overview design vocabulary."""
from dash import dcc, html
from exetat_dashboard.config import AVAILABLE_YEARS, DEFAULT_YEAR, DEFAULT_OPTION, OPTIONS_LIST, PROVINCES_26
from exetat_dashboard.figures.analytics import empty_figure


def card(number, title, subtitle, body, extra_class=""):
    return html.Section([
        html.Div([
            html.H2([html.Span(f"{number:02d}", className="section-number"), html.Span(title)], className="card-title"),
            html.P(subtitle, className="card-subtitle"),
        ], className="card-header"),
    ] + (body if isinstance(body, list) else [body]), className=f"dash-card {extra_class}".strip())


def field(prefix, key, label, options, value, **kwargs):
    return html.Div([
        html.Label(label, htmlFor=f"{prefix}-{key}", className="filter-label"),
        dcc.Dropdown(id=f"{prefix}-{key}", options=options, value=value, clearable=False, **kwargs),
    ], className=f"filter-item analytics-filter-{key}")


def analytics_layout(prefix, school=False):
    entity = "School" if school else "Province"
    filters = [field(prefix, "province", "Province",
                     [{"label": p.title(), "value": p} for p in PROVINCES_26],
                     PROVINCES_26[0] if PROVINCES_26 else None,
                     placeholder="No provinces available")]
    if school:
        filters.append(field(prefix, "school", "School", [], None, searchable=True,
                             placeholder="Select a province, then search for a school"))
    filters.extend([
        field(prefix, "year", "Year", [{"label": str(y), "value": y} for y in AVAILABLE_YEARS],
              DEFAULT_YEAR if DEFAULT_YEAR in AVAILABLE_YEARS else (AVAILABLE_YEARS[-1] if AVAILABLE_YEARS else None),
              placeholder="No years available"),
        field(prefix, "option", "Educational Option", [{"label": o, "value": o} for o in OPTIONS_LIST], DEFAULT_OPTION),
    ])
    graph = lambda name: dcc.Graph(id=f"{prefix}-{name}", figure=empty_figure(),
                                   config={"displayModeBar": False, "responsive": True}, responsive=True,
                                   className="analytics-graph")
    ranking_unit = "students" if school else "schools"
    return html.Div([
        html.Div([
            html.Div([
                html.Div("INSTITUTIONAL INTELLIGENCE" if school else "PROVINCIAL INTELLIGENCE", className="eyebrow"),
                html.H1(f"{entity} Analytics", className="page-title"),
                html.P("Examination outcomes, option leaders and performance over time", className="page-subtitle"),
            ]),
            html.Div([html.Span("TREND WINDOW"), html.Strong("2015–2023")], className="active-dataset"),
        ], className="dashboard-header"),
        html.Div([
            html.Div(filters, className="filters-row analytics-filters"),
            html.Div(id=f"{prefix}-selection-note", className="analytics-selection-note", role="status"),
        ], className="analytics-filter-bar"),
        card(1, f"{entity} Overview", "Selected year and option · comparison with the previous year",
             dcc.Loading(html.Div(id=f"{prefix}-overview"), type="dot")),
        html.Div([
            card(2, "Top Performing Students by Option", "Best recorded score in this selection · change in percentage points",
                 dcc.Loading(html.Div(id=f"{prefix}-leaders"), type="dot")),
            card(3, f"{entity} Performance Trend", "2015–2023 · gaps indicate unavailable rates",
                 dcc.Loading(graph("trend"), type="dot")),
        ], className="analytics-pair"),
        html.Div([
            card(4, "Student Ranking" if school else "School Ranking",
                 "Individual EXETAT percentages" if school else "Weighted success rate · undefined rates listed last", [
                     dcc.Loading(html.Div(id=f"{prefix}-ranking"), type="dot"),
                     html.Button(f"Show all {ranking_unit}", id=f"{prefix}-expand", n_clicks=0,
                                 className="ranking-toggle-btn", style={"display": "none"}),
                     html.Div([
                         html.Button("← Previous", id=f"{prefix}-previous", n_clicks=0, disabled=True, className="ranking-toggle-btn"),
                         html.Span(id=f"{prefix}-page-label", role="status"),
                         html.Button("Next →", id=f"{prefix}-next", n_clicks=0, disabled=True, className="ranking-toggle-btn"),
                     ], id=f"{prefix}-pager", className="analytics-pager", style={"display": "none"}),
                 ]),
            card(5, "Student Percentage Distribution" if school else "Success Rate by Range",
                 "Recorded students only · includes scores below 50%" if school else "Schools per band · excludes unavailable rates",
                 dcc.Loading(graph("distribution"), type="dot")),
        ], className="analytics-pair analytics-pair--ranking"),
        dcc.Store(id=f"{prefix}-paging", data={}),
    ], className="home-page analytics-page")
