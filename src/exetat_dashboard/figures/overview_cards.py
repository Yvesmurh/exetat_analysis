"""
Components for the top of the home page:
- National overview KPI cards (schools / participants / successes / rate)
- Top performing student per educational option
"""

from dash import html

# Minimal inline icon set with government blue strokes
_ICON_SCHOOL = html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23007FFF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M22 10 12 4 2 10l10 6 10-6Z'/><path d='M6 12v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5'/></svg>", alt="School icon")
_ICON_USERS = html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23007FFF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M23 21v-2a4 4 0 0 0-3-3.87'/><path d='M16 3.13a4 4 0 0 1 0 7.75'/></svg>", alt="Users icon")
_ICON_CHECK = html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2310B981' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M22 11.08V12a10 10 0 1 1-5.93-9.14'/><path d='m22 4-10 10-3-3'/></svg>", alt="Check icon")
_ICON_TARGET = html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23007FFF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><circle cx='12' cy='12' r='6'/><circle cx='12' cy='12' r='2'/></svg>", alt="Target icon")

# How many student rows show before the "Show all" toggle is needed —
# mirrors ranking.py's preview cap for the province ranking card.
TOP_STUDENTS_PREVIEW_COUNT = 7


def _fmt_int(value) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def _delta_badge(delta):
    """Small pill showing the YoY change, colored green/red/neutral. Uses an
    arrow glyph alongside color so the signal never relies on color alone."""
    if delta is None:
        return html.Span("No prior-year data", className="delta-badge delta-neutral")

    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
    css_class = "delta-up" if delta > 0 else ("delta-down" if delta < 0 else "delta-neutral")
    return html.Span(f"{arrow} {abs(delta):.2f} pts vs previous year", className=f"delta-badge {css_class}")


def _kpi_card(label: str, value: str, icon=None, extra=None):
    children = []
    if icon is not None:
        children.append(html.Div(icon, className="kpi-icon"))
    children.append(html.Div(label, className="kpi-label"))
    children.append(html.Div(value, className="kpi-value"))
    if extra is not None:
        children.append(extra)
    return html.Div(children, className="kpi-card")


def _overview_trend(overview: dict) -> html.Div:
    """Render the compact year-over-year rate comparison in the overview card."""
    current = overview.get("success_rate")
    delta = overview.get("success_rate_delta_vs_prev_year")
    if current is None or delta is None:
        return html.Div("No prior-year comparison available", className="overview-trend overview-trend--empty")

    try:
        current_rate = float(current)
        previous_rate = current_rate - float(delta)
    except (TypeError, ValueError):
        return html.Div("No prior-year comparison available", className="overview-trend overview-trend--empty")

    delta_class = "delta-up" if delta > 0 else ("delta-down" if delta < 0 else "delta-neutral")
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
    return html.Div(
        [
            html.Div(
                [
                    html.Span("vs previous year", className="overview-trend-label"),
                    html.Span(
                        f"{arrow} {abs(float(delta)):.2f} pts",
                        className=f"overview-trend-delta {delta_class}",
                    ),
                ],
                className="overview-trend-summary",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(f"{previous_rate:.2f}%", className="overview-trend-value"),
                            html.Span("previous", className="overview-trend-year"),
                        ],
                        className="overview-trend-point overview-trend-point--previous",
                    ),
                    html.Div(className="overview-trend-line"),
                    html.Div(
                        [
                            html.Span(f"{current_rate:.2f}%", className="overview-trend-value"),
                            html.Span("current", className="overview-trend-year"),
                        ],
                        className="overview-trend-point overview-trend-point--current",
                    ),
                ],
                className="overview-trend-chart",
            ),
        ],
        className="overview-trend",
    )


def build_overview_cards(overview: dict) -> html.Div:
    """overview: dict returned by queries.overview.get_national_overview()."""
    overview = overview or {}

    if not overview or overview.get("total_participants") in (None, 0) and overview.get("total_schools") in (None, 0):
        return html.Div("No overview data available for this selection.", className="empty-state")

    return html.Div(
        [
            _kpi_card("Total Schools", _fmt_int(overview.get("total_schools")), icon=_ICON_SCHOOL),
            _kpi_card("Total Participants", _fmt_int(overview.get("total_participants")), icon=_ICON_USERS),
            _kpi_card("Successful Students", _fmt_int(overview.get("total_successful")), icon=_ICON_CHECK),
            _kpi_card(
                "National Success Rate",
                _fmt_pct(overview.get("success_rate")),
                icon=_ICON_TARGET,
            ),
			html.Div(_overview_trend(overview), className="overview-trend-wrap"),
        ],
        className="kpi-row",
    )


def _initials(name: str) -> str:
    parts = [p for p in str(name).strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


_MEDALS = ["🥇", "🥈", "🥉"]


def top_students_toggle_label(total_rows: int, show_all: bool, preview_count: int = TOP_STUDENTS_PREVIEW_COUNT) -> str | None:
    """Text for the show-more/show-less button, or None when there's
    nothing to hide (fewer rows than the preview cap) — the caller should
    hide the button entirely in that case, same convention as
    ranking.toggle_button_label()."""
    if total_rows <= preview_count:
        return None
    return "Show top students only ▴" if show_all else f"Show all {total_rows} students ▾"


def build_top_students_table(df, show_all: bool = False, preview_count: int = TOP_STUDENTS_PREVIEW_COUNT) -> html.Div:
    """df: pandas.DataFrame from queries.overview.get_top_students_by_option()
    — one row per educational option (the option's top scorer this year).
    Rendered as compact ranked rows rather than a grid table so it fits the
    dashboard card alongside its rank badges and score deltas.

    By default only the first `preview_count` rows are shown; pass
    show_all=True (wired to a "Show all" toggle button in home.py, the
    same pattern used for the province ranking card) to render every row
    so the user can scroll through the full list instead of it growing
    the card indefinitely."""
    if df is None or df.empty:
        return html.Div("No student results available for this selection.", className="empty-state")

    visible_df = df if show_all else df.head(preview_count)

    rows = []
    for i, (_, row) in enumerate(visible_df.iterrows()):
        name = row.get("top_student_current") or "—"
        option = row.get("option_name") or "—"
        pct = row.get("top_percentage_current")
        pts_change = row.get("pts_change")

        if pts_change is None or pts_change != pts_change:
            change_el = html.Span("No prior-year data", className="student-change delta-neutral")
        else:
            arrow = "▲" if pts_change > 0 else ("▼" if pts_change < 0 else "▬")
            cls = "delta-up" if pts_change > 0 else ("delta-down" if pts_change < 0 else "delta-neutral")
            change_el = html.Span(f"{arrow} {pts_change:+.2f} pts", className=f"student-change {cls}")

        # Medal/rank reflects this student's position in the FULL ranked
        # list (df), not their position within the possibly-sliced
        # visible_df, so ranks stay stable when the list is expanded.
        rank_marker = html.Span(_MEDALS[i], className="student-medal") if i < len(_MEDALS) else html.Span(
            f"{i + 1}", className="student-medal"
        )

        rows.append(
            html.Div(
                [
                    rank_marker,
                    html.Div(_initials(name), className="student-avatar"),
                    html.Div(
                        [
                            html.Div(name, className="student-name"),
                            html.Div(option, className="student-meta"),
                        ],
                        className="student-info",
                    ),
                    html.Div(
                        [
                            html.Div(_fmt_pct(pct), className="student-pct"),
                            change_el,
                        ],
                        className="student-score",
                    ),
                ],
                className="student-row",
            )
        )

    container_class = "row-list row-list--scrollable" if show_all and len(visible_df) > preview_count else "row-list"
    return html.Div(rows, className=container_class)