"""Province Analytics: /provinces. Page callbacks orchestrate shared queries."""
import dash
from dash import Input, Output, State
from exetat_dashboard.components.analytics import analytics_layout
from exetat_dashboard.figures.analytics import (
    build_scope_overview, build_option_leaders, build_scope_trend,
    build_range_distribution, empty_state, empty_figure,
)
from exetat_dashboard.queries.analytics import get_scope_overview, get_scope_trend, get_school_rate_distribution
from exetat_dashboard.queries.overview import get_top_students_by_option
from exetat_dashboard.queries.schools import get_schools
from exetat_dashboard.utils.analytics_callbacks import safe_render, ranking_page

dash.register_page(__name__, path="/provinces", name="Provinces")
PREFIX = "pa"


def layout(**kwargs):
    return analytics_layout(PREFIX)


@dash.callback(
    Output("pa-overview", "children"), Output("pa-leaders", "children"),
    Output("pa-distribution", "figure"), Output("pa-selection-note", "children"),
    Input("pa-province", "value"), Input("pa-year", "value"), Input("pa-option", "value"),
)
def update_analytics(province, current_year, option):
    if not province or current_year is None:
        return empty_state(), empty_state(), empty_figure(), "Select an available province and year."
    return (
        safe_render(lambda: get_scope_overview(province, current_year, option),
                    lambda data: build_scope_overview(data, current_year)),
        safe_render(lambda: get_top_students_by_option(current_year, option, province, raise_on_error=True),
                    lambda df: build_option_leaders(df, current_year)),
        safe_render(lambda: get_school_rate_distribution(province, current_year, option),
                    build_range_distribution, figure=True),
        f"{province} · {current_year} · {option or 'Toutes les options'}",
    )


@dash.callback(Output("pa-trend", "figure"), Input("pa-province", "value"), Input("pa-option", "value"))
def update_trend(province, option):
    if not province:
        return empty_figure()
    # The historical interval is fixed, so changing the current year does not
    # issue an identical trend query again.
    return safe_render(lambda: get_scope_trend(province, option), build_scope_trend, figure=True)


@dash.callback(
    Output("pa-ranking", "children"), Output("pa-expand", "children"), Output("pa-expand", "style"),
    Output("pa-pager", "style"), Output("pa-previous", "disabled"), Output("pa-next", "disabled"),
    Output("pa-page-label", "children"), Output("pa-paging", "data"),
    Input("pa-province", "value"), Input("pa-year", "value"), Input("pa-option", "value"),
    Input("pa-expand", "n_clicks"), Input("pa-previous", "n_clicks"), Input("pa-next", "n_clicks"),
    State("pa-paging", "data"),
)
def update_ranking(province, year, option, _expand, _previous, _next, state):
    return ranking_page(
        lambda limit, offset: get_schools(province, year, option, limit, offset),
        state, [province, year, option], dash.ctx.triggered_id, PREFIX,
        valid=bool(province and year is not None),
    )
