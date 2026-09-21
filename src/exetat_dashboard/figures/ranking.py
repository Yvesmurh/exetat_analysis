"""
Province ranking (highest success rate first). Home page shows the top 5 by
default with a toggle to reveal the rest. Rendered as compact rows with a
progress bar rather than a grid table, per the dashboard's card design.
"""

from dash import html

TOP_N = 5


def _delta_text(delta):
    if delta is None or delta != delta:  # NaN check
        return None
    return delta


def _row(rank: int, province: str, success_rate: float, delta, max_rate: float) -> html.Div:
    pct_label = f"{success_rate * 100:.2f}%"
    width_pct = 0 if max_rate <= 0 else min(100, round((success_rate / max_rate) * 100, 1))

    if delta is None:
        change_el = html.Span("No prior-year data", className="delta-badge delta-neutral")
    else:
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
        cls = "delta-up" if delta > 0 else ("delta-down" if delta < 0 else "delta-neutral")
        change_el = html.Span(f"{arrow} {delta:+.2f} pts", className=f"delta-badge {cls}")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(str(rank), className="ranking-rank"),
                            html.Span(str(province).title(), className="ranking-name"),
                        ],
                        className="ranking-name-block",
                    ),
                    html.Span(pct_label, className="ranking-value"),
                ],
                className="ranking-row-top",
            ),
            html.Div(html.Div(className="progress-fill", style={"width": f"{width_pct}%"}), className="progress-track"),
            html.Div(change_el, className="ranking-row-bottom"),
        ],
        className=f"ranking-row{' ranking-row--top' if rank == 1 else ''}",
    )


def build_ranking_table(df, show_all: bool = False) -> html.Div:
    """df: pandas.DataFrame from queries.province.get_province_stats(), already
    sorted with a `rank` column (1 = highest success rate).

    Returns just the rows (the show-all toggle button is a static element
    owned by pages/home.py — its n_clicks state must survive re-renders of
    this list, so it lives outside the container this function returns)."""
    if df is None or df.empty:
        return html.Div("No province data available for this selection.", className="empty-state")

    visible_df = df if show_all else df.head(TOP_N)
    max_rate = float(df["success_rate"].max()) if not df.empty else 0.0

    rows = [
        _row(
            rank=int(row["rank"]),
            province=row["province"],
            success_rate=float(row["success_rate"]),
            delta=_delta_text(row.get("delta_vs_prev_year")),
            max_rate=max_rate,
        )
        for _, row in visible_df.iterrows()
    ]

    return html.Div(rows, className="row-list")


def toggle_button_label(total_provinces: int, show_all: bool) -> str:
    if total_provinces <= TOP_N:
        return ""
    return "Show top 5 only ▴" if show_all else f"Show all {total_provinces} provinces ▾"
