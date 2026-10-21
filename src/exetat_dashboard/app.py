"""
Dash application entry point.

Run from the project root (the parent directory of the exetat_dashboard/
package) so the `exetat_dashboard.*` absolute imports used throughout the
codebase resolve correctly:

    python -m exetat_dashboard.app
"""

import dash
from dash import dcc, html

from exetat_dashboard.config import COLORS

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="EXETAT — DRC National Education Intelligence",
)
server = app.server

app.layout = html.Div(
    [
        dcc.Location(id="app-location"),
        html.Div(className="gov-flag-bar"),
        html.Nav(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span("EX", className="nav-monogram-text"),
                                html.Span("★", className="nav-monogram-star"),
                            ],
                            className="nav-monogram",
                        ),
                        html.Div(
                            [
                                html.Strong("EXETAT INTELLIGENCE"),
                                html.Small("République Démocratique du Congo · Éducation"),
                            ]
                        ),
                    ],
                    className="nav-brand",
                ),
                html.Div(
                    [
                        dcc.Link("Overview", href="/", id="nav-overview", className="nav-link"),
                        dcc.Link("Provinces", href="/provinces", id="nav-provinces", className="nav-link"),
                        dcc.Link("Schools", href="/schools", id="nav-schools", className="nav-link"),
                    ],
                    className="nav-links",
                ),
                html.Div(
                    [
                        html.Span(className="system-dot"),
                        html.Span("SYSTÈME ANALYTIQUE EN LIGNE", className="system-status-text"),
                    ],
                    className="system-status",
                ),
            ],
            className="navbar",
        ),
        html.Main(dash.page_container, className="page-content"),
        html.Footer(
            [
                html.Div(
                    [
                        html.P(
                            "EXETAT National Education Intelligence — Plateforme d'analyse et de visualisation des résultats éducatifs en RDC.",
                            className="footer-text",
                        ),
                        html.P(
                            "Données compilées à partir des archives publiques des examens d'État. Plateforme indépendante d'aide à la décision pour encadreurs, parents et chercheurs.",
                            className="footer-disclaimer",
                        ),
                    ],
                    className="footer-content",
                ),
            ],
            className="app-footer",
        ),
    ],
    className="app-shell",
)


@app.callback(
    dash.Output("nav-overview", "className"),
    dash.Output("nav-provinces", "className"),
    dash.Output("nav-schools", "className"),
    dash.Input("app-location", "pathname"),
)
def _highlight_active_navigation(pathname):
    active = {"/": 0, "/provinces": 1, "/schools": 2}.get(pathname, 0)
    return tuple("nav-link nav-link--active" if index == active else "nav-link" for index in range(3))


if __name__ == "__main__":
    app.run(debug=True)
