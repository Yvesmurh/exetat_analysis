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
    entity = "Établissement" if school else "Province"
    filters = [field(prefix, "province", "Province",
                     [{"label": p.title(), "value": p} for p in PROVINCES_26],
                     PROVINCES_26[0] if PROVINCES_26 else None,
                     placeholder="Aucune province disponible")]
    if school:
        filters.append(field(prefix, "school", "Établissement", [], None, searchable=True,
                             placeholder="Sélectionnez une province, puis recherchez un établissement"))
    filters.extend([
        field(prefix, "year", "Année", [{"label": str(y), "value": y} for y in AVAILABLE_YEARS],
              DEFAULT_YEAR if DEFAULT_YEAR in AVAILABLE_YEARS else (AVAILABLE_YEARS[-1] if AVAILABLE_YEARS else None),
              placeholder="Aucune année disponible"),
        field(prefix, "option", "Option d'enseignement", [{"label": o, "value": o} for o in OPTIONS_LIST], DEFAULT_OPTION),
    ])
    graph = lambda name: dcc.Graph(id=f"{prefix}-{name}", figure=empty_figure(),
                                   config={"displayModeBar": False, "responsive": True}, responsive=True,
                                   className="analytics-graph")
    ranking_unit = "élèves" if school else "établissements"
    return html.Div([
        html.Div([
            html.Div([
                html.Div("RENSEIGNEMENT INSTITUTIONNEL" if school else "RENSEIGNEMENT PROVINCIAL", className="eyebrow"),
                html.H1(f"Analyses : {entity}", className="page-title"),
                html.P("Résultats aux examens, lauréats par option et évolution des performances", className="page-subtitle"),
            ]),
            html.Div([html.Span("PÉRIODE D'OBSERVATION"), html.Strong("2015–2023")], className="active-dataset"),
        ], className="dashboard-header"),
        html.Div([
            html.Div(filters, className="filters-row analytics-filters"),
            html.Div(id=f"{prefix}-selection-note", className="analytics-selection-note", role="status"),
        ], className="analytics-filter-bar"),
        card(1, f"Vue d'ensemble : {entity}", "Année et option sélectionnées · comparaison avec l'année précédente",
             dcc.Loading(html.Div(id=f"{prefix}-overview"), type="dot")),
        html.Div([
            card(2, "Meilleurs lauréats par option", "Meilleur score enregistré pour cette sélection · variation en points",
                 dcc.Loading(html.Div(id=f"{prefix}-leaders"), type="dot")),
            card(3, f"Évolution des performances : {entity}", "2015–2023 · les interruptions indiquent des données indisponibles",
                 dcc.Loading(graph("trend"), type="dot")),
        ], className="analytics-pair"),
        html.Div([
            card(4, "Classement des élèves" if school else "Classement des établissements",
                 "Pourcentages individuels à l'EXETAT" if school else "Taux de réussite pondéré · taux non définis classés à la fin", [
                     dcc.Loading(html.Div(id=f"{prefix}-ranking"), type="dot"),
                     html.Button(f"Afficher tous les {ranking_unit}", id=f"{prefix}-expand", n_clicks=0,
                                 className="ranking-toggle-btn", style={"display": "none"}),
                     html.Div([
                         html.Button("← Précédent", id=f"{prefix}-previous", n_clicks=0, disabled=True, className="ranking-toggle-btn"),
                         html.Span(id=f"{prefix}-page-label", role="status"),
                         html.Button("Suivant →", id=f"{prefix}-next", n_clicks=0, disabled=True, className="ranking-toggle-btn"),
                     ], id=f"{prefix}-pager", className="analytics-pager", style={"display": "none"}),
                 ]),
            card(5, "Répartition des pourcentages des élèves" if school else "Taux de réussite par tranche",
                 "Élèves enregistrés uniquement · inclut les scores inférieurs à 50%" if school else "Établissements par tranche · exclut les taux indisponibles",
                 dcc.Loading(graph("distribution"), type="dot")),
        ], className="analytics-pair analytics-pair--ranking"),
        dcc.Store(id=f"{prefix}-paging", data={}),
    ], className="home-page analytics-page")
