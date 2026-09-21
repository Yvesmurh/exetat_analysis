"""
map.py
======

Choropleth mapping module for the EXETAT School Rankings Dashboard.

Builds Plotly choropleth figures of the DRC's 26 provinces from
`26provinces_features.json`. The GeoJSON uses `properties.name` for
province names; matching is normalized so database naming differences
do not prevent a province from rendering.

Usage
-----
    from map import create_choropleth

    fig = create_choropleth(
        df,
        location_col="province",
        value_col="pass_rate",
    )
    fig.show()
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from exetat_dashboard.utils.province_names import normalize_province_name

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# __file__-anchored so this works regardless of the caller's cwd
# (consistent with the BASE_DIR pattern already used elsewhere in the project).
#
# Layout: exetat_dashboard/figures/map.py + exetat_dashboard/data/26provinces_features.json
# The GeoJSON lives one level up from this file, in a sibling data/ folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(BASE_DIR, "..", "data", "26provinces_features.json")

# Property in the geojson that (in theory) matches the DB's province naming
# (French, upper-case, e.g. "HAUT-UELE"). Kept for reference/back-compat —
# actual joining now goes through the normalized key below, since the
# hand-reconciled "province" property and the DB column are two
# independently-maintained strings that aren't guaranteed to agree
# byte-for-byte (accents, "-" vs " ", stray whitespace, casing...).
# Property used by the new GeoJSON file.
FEATURE_ID_KEY = "properties.name"

# The property injected by `load_geojson()` holding the *normalized* province
# key (see utils/province_names.normalize_province_name). This is what
# `create_choropleth`/`diagnose_matches` actually join on by default, so a
# single messy name on either side (DB or GeoJSON) no longer silently drops
# that province from the map.
NORMALIZED_FEATURE_ID_KEY = "properties.province_key"
_NORMALIZED_PROPERTY = "province_key"


def load_geojson(path: str = GEOJSON_PATH) -> dict:
    """Load the DRC provinces GeoJSON from disk.

    Also injects a `province_key` property into every feature: the
    normalized (accent-stripped, upper-cased, hyphen/space-insensitive)
    form of `properties.name`. This is what matching is actually done
    against — see NORMALIZED_FEATURE_ID_KEY.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"26provinces_features.json not found at {path}. "
            "map.py resolves this path relative to its own file location "
            "(BASE_DIR = dirname(__file__)) — if you moved map.py, either "
            "move the geojson alongside it or update GEOJSON_PATH."
        )
    with open(path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    for feature in geojson.get("features", []):
        props = feature.setdefault("properties", {})
        props[_NORMALIZED_PROPERTY] = normalize_province_name(props.get("name"))

    return geojson


def diagnose_matches(
    df: pd.DataFrame,
    location_col: str = "province",
    geojson: Optional[dict] = None,
    geojson_path: str = GEOJSON_PATH,
    featureidkey: str = NORMALIZED_FEATURE_ID_KEY,
) -> None:
    """
    Debugging helper — prints which values in df[location_col] DO and DON'T
    match a feature in the geojson. Plotly silently drops any location that
    doesn't find an exact string match via featureidkey, which is why a
    handful of mismatched names can make most of the map disappear while
    the rest of the dashboard (fed by the same query) looks fine.

    By default this compares NORMALIZED values (see
    utils.province_names.normalize_province_name) — the same normalization
    `create_choropleth` uses to actually build the map — so this function's
    report matches what you'll really see rendered. Pass
    featureidkey="properties.name" to instead diagnose *raw* (pre-fix)
    values, e.g. to see the original mismatch that was breaking the map.

    Call this once from a notebook/shell with your real query's output:

        from exetat_dashboard.figures.map import diagnose_matches
        from exetat_dashboard.queries.province import get_province_stats
        df = get_province_stats(2023, None)
        diagnose_matches(df)
    """
    if geojson is None:
        geojson = load_geojson(geojson_path)

    # featureidkey is a dotted path like "properties.name"
    prop_name = featureidkey.split(".", 1)[1]
    normalized = prop_name == _NORMALIZED_PROPERTY

    geo_values = {f["properties"][prop_name] for f in geojson["features"]}
    raw_df_values = df[location_col].dropna().unique()
    if normalized:
        df_values = {normalize_province_name(v) for v in raw_df_values}
    else:
        df_values = set(raw_df_values)

    matched = df_values & geo_values
    unmatched_in_df = sorted(v for v in (df_values - geo_values) if v is not None)
    unmatched_in_geo = sorted(v for v in (geo_values - df_values) if v is not None)

    print(f"GeoJSON provinces: {len(geo_values)}")
    print(f"DataFrame provinces: {len(df_values)}")
    print(f"Matched: {len(matched)}")
    print(f"Unmatched: {len(unmatched_in_df) + len(unmatched_in_geo)}\n")

    if unmatched_in_df:
        print("In df but NOT found in geojson (won't render on the map):")
        for v in unmatched_in_df:
            print(f"  {v!r}")
        print()

    if unmatched_in_geo:
        print("In geojson but NOT found in df (will render with no data / blank):")
        for v in unmatched_in_geo:
            print(f"  {v!r}")


def create_choropleth(
    df: pd.DataFrame,
    location_col: str = "province",
    value_col: str = "value",
    geojson: Optional[dict] = None,
    geojson_path: str = GEOJSON_PATH,
    featureidkey: str = NORMALIZED_FEATURE_ID_KEY,
    colorscale: str = "YlGnBu",
    title: Optional[str] = None,
    colorbar_title: Optional[str] = None,
    hover_name_col: Optional[str] = None,
    hover_cols: Optional[list[str]] = None,
    hover_labels: Optional[dict[str, str]] = None,
    zmid: Optional[float] = None,
    selected_location: Optional[str] = None,
) -> go.Figure:
    """
    Build a choropleth map of the DRC's 26 provinces.

    Parameters
    ----------
    df : pd.DataFrame
        Data containing at least `location_col` and `value_col`.
        Values in `location_col` are matched to the GeoJSON's `name`
        property after normalization.
    location_col : str
        Column in `df` with province names.
    value_col : str
        Column in `df` with the numeric value to color by
        (e.g. pass rate, average score, number of schools).
    geojson : dict, optional
        Pre-loaded geojson dict. If omitted, loaded from `geojson_path`.
    geojson_path : str
        Path to the geojson file (defaults to the file next to this module).
    featureidkey : str
        Path within each geojson feature used to match `location_col`.
    colorscale : str
        Plotly colorscale name.
    title : str, optional
        Figure title.
    colorbar_title : str, optional
        Label for the color bar. Defaults to `value_col`.
    hover_name_col : str, optional
        Column to show as the hover title instead of the raw province code.
    hover_cols : list[str], optional
        Extra columns from `df` to show as additional lines in the hover
        tooltip (e.g. ["num_schools", "num_participants", "rate_change_pts"]).
    hover_labels : dict[str, str], optional
        Display label overrides for `hover_cols`, e.g. {"rate_change_pts": "YoY change (pts)"}.
        Columns not listed fall back to their raw column name.
    zmid : float, optional
        Center point of the colorscale (e.g. 0, for a diverging scale showing
        year-over-year change where positive/negative should diverge from white).
    selected_location : str, optional
        A value from `location_col` to visually highlight (thicker border)
        — e.g. the province currently picked in a filter dropdown.

    Returns
    -------
    go.Figure
    """
    if geojson is None:
        geojson = load_geojson(geojson_path)

    missing = {location_col, value_col} - set(df.columns)
    if missing:
        raise ValueError(f"df is missing required column(s): {missing}")

    hover_text = df[hover_name_col] if hover_name_col else df[location_col]
    hover_labels = hover_labels or {}

    # Join key actually sent to Plotly. When matching against the geojson's
    # normalized property (the default), normalize the df's raw province
    # names the same way, so accent/case/hyphen-vs-space differences between
    # the DB and the GeoJSON no longer drop provinces from the map. The
    # original df[location_col] values are untouched and still used for the
    # hover text / `selected_location` highlight below.
    prop_name = featureidkey.split(".", 1)[1]
    if prop_name == _NORMALIZED_PROPERTY:
        location_values = df[location_col].map(normalize_province_name)
        selected_location = normalize_province_name(selected_location)
    else:
        location_values = df[location_col]

    # Build the extra hover lines + customdata array, if requested.
    extra_lines = ""
    customdata = None
    if hover_cols:
        missing_hover = set(hover_cols) - set(df.columns)
        if missing_hover:
            raise ValueError(f"hover_cols not found in df: {missing_hover}")
        customdata = df[hover_cols].to_numpy()
        for i, col in enumerate(hover_cols):
            label = hover_labels.get(col, col)
            extra_lines += f"{label}: %{{customdata[{i}]}}<br>"

    # Thicker/darker border on the selected province, if any.
    line_widths = [
        1.8 if selected_location and loc == selected_location else 0.6
        for loc in location_values
    ]
    line_colors = [
        "#00E5FF" if selected_location and loc == selected_location else "#284A63"
        for loc in location_values
    ]

    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            locations=location_values,
            z=df[value_col],
            featureidkey=featureidkey,
            colorscale=colorscale,
            zmid=zmid,
            marker_line_color=line_colors,
            marker_line_width=line_widths,
            colorbar=dict(
                title=dict(text=colorbar_title or value_col, font=dict(color="#9BB0C3", size=9)),
                thickness=10,
                len=0.62,
                x=0.99,
                tickfont=dict(color="#9BB0C3", size=9),
                outlinewidth=0,
                bgcolor="rgba(5,11,22,0.42)",
            ),
            hovertext=hover_text,
            customdata=customdata,
            hovertemplate="<b>%{hovertext}</b><br>"
            + f"{colorbar_title or value_col}: "
            + "%{z}<br>"
            + extra_lines
            + "<extra></extra>",
        )
    )

    # No basemap needed — zoom tightly to the provinces themselves.
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(
        title=title,
        autosize=True,
        margin=dict(l=0, r=0, t=50 if title else 10, b=0),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#EDF8FF"),
        hoverlabel=dict(bgcolor="#07111F", bordercolor="#00A8FF", font=dict(color="#EDF8FF", size=11)),
        transition=dict(duration=280, easing="cubic-in-out"),
    )

    return fig


if __name__ == "__main__":
    # Quick smoke test with random data over the 26 provinces
    import random

    geo = load_geojson()
    provinces = [f["properties"]["name"] for f in geo["features"]]

    sample_df = pd.DataFrame(
        {
            "province": provinces,
            "pass_rate": [round(random.uniform(40, 95), 1) for _ in provinces],
        }
    )

    test_fig = create_choropleth(
        sample_df,
        location_col="province",
        value_col="pass_rate",
        title="EXETAT Pass Rate by Province (sample data)",
        colorbar_title="Pass rate (%)",
    )
    test_fig.write_html(os.path.join(BASE_DIR, "map_smoke_test.html"))
    print("Smoke test OK -> map_smoke_test.html")

    # Second smoke test: deliberately "messy" province names (accents,
    # spaces instead of hyphens, mixed case, stray whitespace) — simulates
    # a DB column that doesn't byte-for-byte match the GeoJSON's `province`
    # property, which is what broke the real map down to a single matching
    # feature. diagnose_matches() should report 26/26 matched afterwards.
    def _messify(name: str) -> str:
        variants = [
            name.title(),
            name.replace("-", " "),
            f" {name.lower()} ",
            name.replace("E", "É", 1),
        ]
        return random.choice(variants)

    messy_df = pd.DataFrame(
        {
            "province": [_messify(p) for p in provinces],
            "pass_rate": [round(random.uniform(40, 95), 1) for _ in provinces],
        }
    )
    print("\n--- diagnose_matches() on deliberately messy province names ---")
    diagnose_matches(messy_df)
    messy_fig = create_choropleth(messy_df, location_col="province", value_col="pass_rate")
    print(f"Messy-name matched trace locations: {sum(v is not None for v in messy_fig.data[0].locations)}/26")
