"""Province ranking (highest success rate first), rendered as compact,
scrollable rows with a progress bar per province."""

from dash import html


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

    rank_class = f"ranking-rank ranking-rank--{rank}" if rank <= 3 else "ranking-rank"
    top_class = f" ranking-row--top ranking-row--top{rank}" if rank <= 3 else ""

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(str(rank), className=rank_class),
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
        className=f"ranking-row{top_class}",
    )


def build_ranking_table(df) -> html.Div:
    """df: pandas.DataFrame from queries.province.get_province_stats(), already
    sorted with a `rank` column (1 = highest success rate)."""
    if df is None or df.empty:
        return html.Div("No province data available for this selection.", className="empty-state")

    max_rate = float(df["success_rate"].max()) if not df.empty else 0.0

    rows = [
        _row(
            rank=int(row["rank"]),
            province=row["province"],
            success_rate=float(row["success_rate"]),
            delta=_delta_text(row.get("delta_vs_prev_year")),
            max_rate=max_rate,
        )
        for _, row in df.iterrows()
    ]

    return html.Div(rows, className="row-list row-list--scrollable")
