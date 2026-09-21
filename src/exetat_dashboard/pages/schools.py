"""School Analytics: /schools. All result queries also validate province scope."""
import dash
from dash import Input, Output, State
from exetat_dashboard.components.analytics import analytics_layout
from exetat_dashboard.figures.analytics import (
    build_scope_overview, build_option_leaders, build_scope_trend,
    build_range_distribution, empty_state, empty_figure,
)
from exetat_dashboard.queries.analytics import get_scope_overview, get_scope_trend, get_school_student_distribution
from exetat_dashboard.queries.helpers import QueryError
from exetat_dashboard.queries.overview import get_top_students_by_option
from exetat_dashboard.queries.schools import get_school_choices, get_student_ranking
from exetat_dashboard.utils.analytics_callbacks import safe_render, ranking_page

dash.register_page(__name__, path="/schools", name="Schools")
PREFIX = "sa"


def layout(**kwargs):
    return analytics_layout(PREFIX, school=True)


@dash.callback(
    Output("sa-school", "options"), Output("sa-school", "value"), Output("sa-school", "placeholder"),
    Input("sa-province", "value"), Input("sa-school", "search_value"),
    State("sa-school", "value"),
)
def update_school_selector(province, search, selected_school):
    if not province:
        return [], None, "Select a province first"
    # Discard the old province's search text and selection when switching.
    province_changed = dash.ctx.triggered_id in (None, "sa-province")
    if province_changed:
        search, selected_school = "", None
    try:
        choices = get_school_choices(province, search, selected_school)
    except QueryError:
        return [], None, "Schools temporarily unavailable"
    ids = {choice["value"] for choice in choices}
    if selected_school not in ids:
        # Searching should not unexpectedly select a school on every keystroke.
        selected_school = choices[0]["value"] if choices and province_changed else None
    return choices, selected_school, "Search schools in this province" if choices else "No matching schools"


@dash.callback(
    Output("sa-overview", "children"), Output("sa-leaders", "children"),
    Output("sa-distribution", "figure"), Output("sa-selection-note", "children"),
    Input("sa-province", "value"), Input("sa-school", "value"),
    Input("sa-year", "value"), Input("sa-option", "value"),
)
def update_analytics(province, school_id, current_year, option):
    if not province or school_id is None or current_year is None:
        return empty_state(), empty_state(), empty_figure(), "Select an available province, school and year."
    return (
        safe_render(lambda: get_scope_overview(province, current_year, option, school_id),
                    lambda data: build_scope_overview(data, current_year, school=True)),
        safe_render(lambda: get_top_students_by_option(current_year, option, province, school_id, raise_on_error=True),
                    lambda df: build_option_leaders(df, current_year)),
        safe_render(lambda: get_school_student_distribution(province, school_id, current_year, option),
                    lambda df: build_range_distribution(df, school=True), figure=True),
        f"{province} · {current_year} · {option or 'Toutes les options'} · Search lists up to 50 matching schools.",
    )


@dash.callback(Output("sa-trend", "figure"), Input("sa-province", "value"),
               Input("sa-school", "value"), Input("sa-option", "value"))
def update_trend(province, school_id, option):
    if not province or school_id is None:
        return empty_figure()
    return safe_render(lambda: get_scope_trend(province, option, school_id), build_scope_trend, figure=True)


@dash.callback(
    Output("sa-ranking", "children"), Output("sa-expand", "children"), Output("sa-expand", "style"),
    Output("sa-pager", "style"), Output("sa-previous", "disabled"), Output("sa-next", "disabled"),
    Output("sa-page-label", "children"), Output("sa-paging", "data"),
    Input("sa-province", "value"), Input("sa-school", "value"),
    Input("sa-year", "value"), Input("sa-option", "value"),
    Input("sa-expand", "n_clicks"), Input("sa-previous", "n_clicks"), Input("sa-next", "n_clicks"),
    State("sa-paging", "data"),
)
def update_ranking(province, school_id, year, option, _expand, _previous, _next, state):
    return ranking_page(
        lambda limit, offset: get_student_ranking(province, school_id, year, option, limit, offset),
        state, [province, school_id, year, option], dash.ctx.triggered_id, PREFIX,
        valid=bool(province and school_id is not None and year is not None), school=True,
    )
