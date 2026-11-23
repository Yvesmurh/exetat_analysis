"""
Student-Centered Schools & Alumni Discovery: /schools

Allows former EXETAT students to identify their examination record,
reconnect with their graduating classmates, explore educational options offered
at their school, and visualize their school's 5-year performance history.
"""
import dash
from dash import Input, Output, State, ctx, dcc, html
import pandas as pd
import plotly.graph_objects as go

from exetat_dashboard.config import AVAILABLE_YEARS, DEFAULT_YEAR, COLORS, FONT_FAMILY
from exetat_dashboard.figures.overview_cards import (
    _kpi_card, _fmt_int, _ICON_SCHOOL, _ICON_USERS, _ICON_CHECK, _ICON_TARGET,
)
from exetat_dashboard.queries.schools import (
    search_students, get_school_classmates, get_school_options_summary, get_school_history_5years,
)

dash.register_page(__name__, path="/schools", name="Établissements scolaires")


def percentage_text(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.2f}%"


def build_school_5year_trend(df_history, end_year):
    """Build interactive Plotly line chart for 5-year school performance.

    Missing years appear as gaps (connectgaps=False), never estimated.
    """
    start_year = int(end_year) - 4
    all_years = list(range(start_year, int(end_year) + 1))

    if df_history is None or df_history.empty:
        df_indexed = pd.DataFrame({"year": all_years, "success_rate": [None] * len(all_years)})
    else:
        df_indexed = df_history.set_index("year").reindex(all_years).reset_index()

    y_values = [None if pd.isna(v) else round(float(v), 2) for v in df_indexed["success_rate"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_years,
        y=y_values,
        mode="lines+markers",
        connectgaps=False,  # Gaps indicate unavailable years; never estimated
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=8, color=COLORS["primary"], line=dict(color="#FFFFFF", width=2)),
        hovertemplate="Année %{x}<br>Taux de réussite : %{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        autosize=True,
        height=280,
        margin=dict(l=55, r=25, t=20, b=45),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, size=12.5, color=COLORS["text"]),
        hovermode="x unified",
        xaxis=dict(
            title=dict(text="Année d'examen", font=dict(family=FONT_FAMILY, size=12, color=COLORS["text"])),
            dtick=1,
            range=[start_year - 0.35, int(end_year) + 0.35],
            showgrid=False,
            linecolor="#E2E8F0",
            tickfont=dict(family=FONT_FAMILY, size=12, color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            title=dict(text="Taux de réussite (%)", font=dict(family=FONT_FAMILY, size=12, color=COLORS["text"])),
            ticksuffix="%",
            range=[0, 105],
            gridcolor="#F1F5F9",
            zeroline=False,
            tickfont=dict(family=FONT_FAMILY, size=12, color=COLORS["text_secondary"]),
        ),
    )
    return fig


def layout(**kwargs):
    default_year = DEFAULT_YEAR if DEFAULT_YEAR in AVAILABLE_YEARS else (AVAILABLE_YEARS[-1] if AVAILABLE_YEARS else 2023)
    year_options = [{"label": str(y), "value": y} for y in AVAILABLE_YEARS]

    return html.Div([
        # Page Title Banner
        html.Div([
            html.Div([
                html.Div("ANCIENS ÉLÈVES & MÉMOIRE INSTITUTIONNELLE", className="eyebrow"),
                html.H1("Recherche d'Établissements & Anciens Élèves", className="page-title"),
                html.P("Retrouvez votre promotion de l'EXETAT, découvrez les options organisées et suivez l'historique de votre établissement.", className="page-subtitle"),
            ]),
        ], className="dashboard-header"),

        # Section 1: Student Identification Card
        html.Section([
            html.Div([
                html.H2([
                    html.Span("01", className="section-number"),
                    html.Span("Identification de l'élève"),
                ], className="card-title"),
                html.P("Recherchez votre palmarès à l'EXETAT à l'aide de votre nom complet et de l'année d'examen.", className="card-subtitle"),
            ], className="card-header"),
            html.Div([
                html.Div([
                    html.Div([
                        html.Label("Nom complet de l'élève", htmlFor="stu-search-name", className="filter-label"),
                        dcc.Input(
                            id="stu-search-name",
                            type="text",
                            placeholder="Entrez le nom complet (ex. Kakesa Bankini)...",
                            className="student-search-input",
                            debounce=True,
                        ),
                    ], className="student-search-field"),
                    html.Div([
                        html.Label("Année d'examen", htmlFor="stu-search-year", className="filter-label"),
                        dcc.Dropdown(
                            id="stu-search-year",
                            options=year_options,
                            value=default_year,
                            clearable=False,
                            className="student-search-year-dropdown",
                        ),
                    ], className="student-search-field student-search-field--year"),
                    html.Button([
                        html.Span("🔍"),
                        html.Span(" Rechercher"),
                    ], id="stu-search-btn", n_clicks=0, className="student-search-btn"),
                ], className="student-search-bar"),

                # Search feedback / candidate selection container
                dcc.Loading(
                    html.Div(id="stu-search-feedback", className="student-search-container", style={"padding": "16px 24px"}),
                    type="dot",
                ),
            ]),
        ], className="dash-card"),

        # Hidden stores for reactive state
        dcc.Store(id="stu-current-student", data=None),
        dcc.Store(id="stu-candidates-store", data=[]),
        dcc.Store(id="stu-classmates-raw-store", data=[]),

        # Dynamic Content Container: Sections 2, 3, and 4
        dcc.Loading(
            html.Div(id="stu-dashboard-content"),
            type="dot",
        ),
    ], className="home-page analytics-page")


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@dash.callback(
    Output("stu-search-feedback", "children"),
    Output("stu-candidates-store", "data"),
    Output("stu-current-student", "data"),
    Input("stu-search-btn", "n_clicks"),
    Input("stu-search-name", "n_submit"),
    State("stu-search-name", "value"),
    State("stu-search-year", "value"),
    prevent_initial_call=False,
)
def handle_student_search(n_clicks, n_submit, name, year):
    """Search for students and manage single-match vs multiple-match states."""
    if not n_clicks and not n_submit:
        return (
            html.Div(
                "Entrez votre nom complet et votre année d'examen ci-dessus, puis cliquez sur « Rechercher » pour localiser vos condisciples et votre établissement.",
                className="empty-state",
            ),
            [],
            dash.no_update,
        )

    if not name or not str(name).strip():
        return (
            html.Div(
                "Veuillez entrer le nom d'un élève à rechercher.",
                className="empty-state",
                style={"color": COLORS["warning"]},
            ),
            [],
            None,
        )

    try:
        df = search_students(name, year, limit=50)
    except Exception as exc:
        return (
            html.Div(
                "Une erreur est survenue lors de la recherche dans la base de données. Veuillez réessayer.",
                className="empty-state",
                style={"color": COLORS["danger"]},
            ),
            [],
            None,
        )

    if df is None or df.empty:
        return (
            html.Div(
                f"Aucun palmarès EXETAT trouvé pour « {name} » en {year}. Veuillez vérifier l'orthographe ou l'année d'examen.",
                className="empty-state",
                style={"color": COLORS["danger"]},
            ),
            [],
            None,
        )

    records = df.to_dict("records")

    # Single student match: directly select
    if len(records) == 1:
        single = records[0]
        return (
            html.Div([
                html.Span("✓ Palmarès identifié : ", style={"fontWeight": "700", "color": COLORS["success"]}),
                html.Span(f"{single['student_name']} · {single['school_name']} ({single['province_name']})"),
            ], className="analytics-selection-note"),
            records,
            single,
        )

    # Multiple matching students: prompt user to pick their exact record
    candidate_cards = [
        html.Div([
            html.Div([
                html.Div(rec["student_name"], className="candidate-info-name"),
                html.Div([
                    html.Strong(f"Établissement : {rec['school_name']}"),
                    html.Span(f" · Code : {rec['school_code'] or '—'} · Province : {rec['province_name']}"),
                    html.Br(),
                    html.Span(f"Option : {rec['option_name']}"),
                    html.Span(f" · Pourcentage : {percentage_text(rec['percentage'])}"),
                ], className="candidate-info-meta"),
            ]),
            html.Button(
                "Sélectionner ce palmarès →",
                id={"type": "stu-candidate-btn", "index": i},
                n_clicks=0,
                className="candidate-select-btn",
            ),
        ], className="student-candidate-card")
        for i, rec in enumerate(records)
    ]

    return (
        html.Div([
            html.Div(
                f"{len(records)} palmarès trouvés pour « {name} » en {year}. Veuillez sélectionner le vôtre ci-dessous :",
                style={"fontWeight": "600", "color": COLORS["navy"], "marginBottom": "10px", "fontSize": "14px"},
            ),
            html.Div(candidate_cards, className="student-candidate-list"),
        ]),
        records,
        None,
    )


@dash.callback(
    Output("stu-current-student", "data", allow_duplicate=True),
    Input({"type": "stu-candidate-btn", "index": dash.ALL}, "n_clicks"),
    State("stu-candidates-store", "data"),
    prevent_initial_call=True,
)
def handle_candidate_selection(n_clicks_list, candidates):
    """Set the active student record when clicked from multiple candidates."""
    if not ctx.triggered_id or not any(n_clicks_list):
        return dash.no_update
    idx = ctx.triggered_id["index"]
    if 0 <= idx < len(candidates):
        return candidates[idx]
    return dash.no_update


@dash.callback(
    Output("stu-current-student", "data", allow_duplicate=True),
    Input("stu-reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_reset_student(n_clicks):
    """Allow user to reset selected student and perform another search."""
    if n_clicks:
        return None
    return dash.no_update


@dash.callback(
    Output("stu-dashboard-content", "children"),
    Output("stu-classmates-raw-store", "data"),
    Input("stu-current-student", "data"),
)
def render_student_dashboard(student):
    """Render Student Profile, Classmates, Educational Options, and 5-Year History."""
    if not student:
        return html.Div(), []

    school_id = student.get("school_id")
    exam_year = student.get("exam_year")
    school_name = student.get("school_name", "Établissement")
    school_code = student.get("school_code") or "—"
    province_name = student.get("province_name", "—")
    student_name = student.get("student_name", "Élève")
    student_code = student.get("student_code") or "—"
    option_name = student.get("option_name", "—")
    percentage_score = percentage_text(student.get("percentage"))

    # Fetch data
    df_classmates = get_school_classmates(school_id, exam_year)
    df_options = get_school_options_summary(school_id, exam_year)
    df_history = get_school_history_5years(school_id, exam_year)

    raw_classmates = df_classmates.to_dict("records") if df_classmates is not None and not df_classmates.empty else []
    total_classmates = len(raw_classmates)
    total_options = len(df_options) if df_options is not None and not df_options.empty else 0

    # -----------------------------------------------------------------------
    # 1. Student Profile Hero Card
    # -----------------------------------------------------------------------
    profile_hero = html.Div([
        html.Div([
            html.Div([
                html.Div("PROFIL DE L'ÉLÈVE", className="profile-status-subtitle"),
                html.H2(student_name, className="profile-name-title"),
                html.Div(f"Candidat EXETAT · Promotion {exam_year}", style={"color": "#BFDBFE", "fontSize": "13px"}),
            ]),
            html.Button("← Rechercher un autre élève", id="stu-reset-btn", n_clicks=0, className="profile-reset-btn"),
        ], className="profile-hero-top"),

        html.Div([
            html.Div([
                html.Div("Établissement", className="profile-detail-label"),
                html.Div(school_name, className="profile-detail-value"),
            ], className="profile-detail-item"),
            html.Div([
                html.Div("Code établissement", className="profile-detail-label"),
                html.Div(school_code, className="profile-detail-value"),
            ], className="profile-detail-item"),
            html.Div([
                html.Div("Province", className="profile-detail-label"),
                html.Div(province_name, className="profile-detail-value"),
            ], className="profile-detail-item"),
            html.Div([
                html.Div("Édition EXETAT", className="profile-detail-label"),
                html.Div(str(exam_year), className="profile-detail-value"),
            ], className="profile-detail-item"),
            html.Div([
                html.Div("Option d'enseignement", className="profile-detail-label"),
                html.Div(option_name, className="profile-detail-value"),
            ], className="profile-detail-item"),
            html.Div([
                html.Div("Pourcentage EXETAT", className="profile-detail-label"),
                html.Div(html.Span(percentage_score, className="profile-score-badge"), className="profile-detail-value"),
            ], className="profile-detail-item"),
        ], className="profile-details-grid"),
    ], className="student-profile-hero")

    # -----------------------------------------------------------------------
    # 2. "Your EXETAT Classmates" Section
    # -----------------------------------------------------------------------
    classmates_section = html.Section([
        html.Div([
            html.H2([
                html.Span("02", className="section-number"),
                html.Span("Vos condisciples de promotion"),
            ], className="card-title"),
            html.P(f"Tous les diplômés de {school_name} pour l'édition {exam_year}.", className="card-subtitle"),
        ], className="card-header"),

        html.Div([
            html.Div([
                html.Div([
                    html.Span("Total des condisciples : ", style={"fontWeight": "600"}),
                    html.Span(f"{total_classmates}", style={"fontWeight": "700", "color": COLORS["primary"]}),
                ], className="classmates-counter"),
                dcc.Input(
                    id="stu-classmates-filter",
                    type="text",
                    placeholder="Rechercher des condisciples par nom...",
                    className="classmates-search-input",
                    debounce=True,
                ),
            ], className="classmates-controls-bar"),

            dcc.Loading(
                html.Div(id="stu-classmates-table-container"),
                type="dot",
            ),
        ]),
    ], className="dash-card")

    # -----------------------------------------------------------------------
    # 3. "Educational Options at Your School" Section
    # -----------------------------------------------------------------------
    options_rows = []
    if df_options is not None and not df_options.empty:
        for row in df_options.itertuples():
            options_rows.append(html.Tr([
                html.Td(row.option_name, style={"fontWeight": "600", "color": COLORS["navy"]}),
                html.Td(_fmt_int(row.participants)),
                html.Td(_fmt_int(row.successes)),
                html.Td(percentage_text(row.success_rate), className="analytics-score"),
            ]))
    else:
        options_rows.append(html.Tr([
            html.Td("Aucun résultat disponible sur les options pour cette année.", colSpan=4, className="empty-state"),
        ]))

    options_table = html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th("Option d'enseignement", scope="col"),
                html.Th("Participants", scope="col"),
                html.Th("Réussites", scope="col"),
                html.Th("Taux de réussite", scope="col"),
            ])),
            html.Tbody(options_rows),
        ], className="analytics-table"),
        className="analytics-table-scroll",
        tabIndex=0,
    )

    options_section = html.Section([
        html.Div([
            html.H2([
                html.Span("03", className="section-number"),
                html.Span("Options d'enseignement organisées"),
            ], className="card-title"),
            html.P(f"Aperçu des options organisées à {school_name} en {exam_year} ({total_options} options au total).", className="card-subtitle"),
        ], className="card-header"),
        html.Div(options_table, style={"padding": "0"}),
    ], className="dash-card")

    # -----------------------------------------------------------------------
    # 4. "Your School's Performance Over Time" Section
    # -----------------------------------------------------------------------
    trend_figure = build_school_5year_trend(df_history, exam_year)

    history_rows = []
    start_year = int(exam_year) - 4
    all_5_years = list(range(start_year, int(exam_year) + 1))
    df_history_indexed = df_history.set_index("year").reindex(all_5_years).reset_index() if df_history is not None else pd.DataFrame({"year": all_5_years})

    for row in df_history_indexed.itertuples():
        y = int(row.year)
        p = getattr(row, "participants", None)
        s = getattr(row, "successes", None)
        r = getattr(row, "success_rate", None)

        p_display = _fmt_int(p) if pd.notna(p) else "—"
        s_display = _fmt_int(s) if pd.notna(s) else "—"
        r_display = percentage_text(r) if pd.notna(r) else "— (Donnée indisponible)"

        is_grad_year = (y == int(exam_year))
        row_style = {"backgroundColor": "#F8FAFC", "fontWeight": "700"} if is_grad_year else {}

        history_rows.append(html.Tr([
            html.Td([
                html.Span(str(y)),
                html.Span(" (Votre année)", className="you-badge") if is_grad_year else "",
            ]),
            html.Td(p_display),
            html.Td(s_display),
            html.Td(r_display, className="analytics-score"),
        ], style=row_style))

    history_table = html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th("Année", scope="col"),
                html.Th("Participants", scope="col"),
                html.Th("Réussites", scope="col"),
                html.Th("Taux de réussite", scope="col"),
            ])),
            html.Tbody(history_rows),
        ], className="analytics-table"),
        className="analytics-table-scroll",
        tabIndex=0,
    )

    history_section = html.Section([
        html.Div([
            html.H2([
                html.Span("04", className="section-number"),
                html.Span("Évolution des performances de l'établissement"),
            ], className="card-title"),
            html.P(f"Rétrospective quinquennale jusqu'à l'édition {exam_year} ({start_year}–{exam_year}). Les interruptions indiquent des données manquantes.", className="card-subtitle"),
        ], className="card-header"),
        html.Div([
            dcc.Graph(
                id="stu-5year-trend-chart",
                figure=trend_figure,
                config={"displayModeBar": False, "responsive": True},
                className="analytics-graph",
            ),
            html.Div(history_table, style={"marginTop": "16px"}),
        ], style={"padding": "16px 20px"}),
    ], className="dash-card")

    content = html.Div([
        profile_hero,
        classmates_section,
        html.Div([
            options_section,
            history_section,
        ], className="analytics-pair"),
    ], style={"marginTop": "24px"})

    return content, raw_classmates


@dash.callback(
    Output("stu-classmates-table-container", "children"),
    Input("stu-classmates-filter", "value"),
    Input("stu-classmates-raw-store", "data"),
    State("stu-current-student", "data"),
)
def filter_classmates_table(search_query, raw_classmates, current_student):
    """Filter and render classmates table, highlighting the identified student."""
    if not raw_classmates:
        return html.Div("Aucun condisciple trouvé pour cet établissement et cette année d'examen.", className="empty-state")

    current_id = current_student.get("student_id") if current_student else None

    # Filter by name if search query is present
    filtered = raw_classmates
    if search_query and str(search_query).strip():
        q = str(search_query).strip().lower()
        filtered = [c for c in raw_classmates if q in str(c.get("student_name", "")).lower()]

    if not filtered:
        return html.Div(f"Aucun condisciple ne correspond à « {search_query} ».", className="empty-state")

    rows = []
    for row in filtered:
        is_current = (current_id is not None and row.get("student_id") == current_id)
        row_class = "classmate-row--current" if is_current else ""

        name_content = [
            html.Span(row.get("student_name", "—")),
        ]
        if is_current:
            name_content.append(html.Span("Vous", className="you-badge"))

        rows.append(html.Tr([
            html.Td(html.Span(str(row.get("rank", "—")), className="ranking-rank")),
            html.Td(name_content),
            html.Td(row.get("option_name") or "—"),
            html.Td(percentage_text(row.get("percentage")), className="analytics-score"),
        ], className=row_class))

    return html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th("Rang", scope="col", style={"width": "70px"}),
                html.Th("Nom de l'élève", scope="col"),
                html.Th("Option d'enseignement", scope="col"),
                html.Th("Pourcentage obtenu", scope="col", style={"width": "140px"}),
            ])),
            html.Tbody(rows),
        ], className="analytics-table"),
        className="analytics-table-scroll",
        tabIndex=0,
    )
