"""
Dash application entry point.

Run from the project root (the parent directory of the exetat_dashboard/
package) so the `exetat_dashboard.*` absolute imports used throughout the
codebase resolve correctly:

    python -m exetat_dashboard.app
"""

import dash
from dash import dcc, html
from flask import send_from_directory
from pathlib import Path


from exetat_dashboard.config import COLORS
from exetat_dashboard.translations import (
    APP_TITLE,
    FOOTER_DISCLAIMER,
    FOOTER_TEXT,
    NAV_BRAND_SUBTITLE,
    NAV_OVERVIEW,
    NAV_PROVINCES,
    NAV_SCHOOLS,
    NAV_SYSTEM_STATUS,
)


BASE_DIR = Path(__file__).resolve().parents[2]
CUSTOM_PAGES_DIR = BASE_DIR / "custom_pages"

@server.route("/my-page")
def my_page():
    return send_from_directory(CUSTOM_PAGES_DIR, "my_page.html")

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
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
                                html.Small(NAV_BRAND_SUBTITLE),
                            ]
                        ),
                    ],
                    className="nav-brand",
                ),
                html.Div(
                    [
                        dcc.Link(NAV_OVERVIEW, href="/", id="nav-overview", className="nav-link"),
                        dcc.Link(NAV_PROVINCES, href="/provinces", id="nav-provinces", className="nav-link"),
                        dcc.Link(NAV_SCHOOLS, href="/schools", id="nav-schools", className="nav-link"),
                    ],
                    className="nav-links",
                ),
                html.Div(
                    [
                        html.Span(className="system-dot"),
                        html.Span(NAV_SYSTEM_STATUS, className="system-status-text"),
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
                            FOOTER_TEXT,
                            className="footer-text",
                        ),
                        html.P(
                            FOOTER_DISCLAIMER,
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


def main():
    import os

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8050"))

    app.run(
        host=host,
        port=port,
        debug=False
    )


if __name__ == "__main__":
    main()


