import os
import sys
from pathlib import Path

from exetat_dashboard.queries.helpers import get_connection


# ---------------------------------------------------------------------------
# App constants
# ---------------------------------------------------------------------------
try:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT years FROM exetat_entry ORDER BY years")
            AVAILABLE_YEARS = [row[0] for row in cursor.fetchall()]

        DEFAULT_YEAR = 2023
        DEFAULT_OPTION = "Toutes les options"

        with conn.cursor() as cursor:
            cursor.execute("SELECT option_name FROM options ORDER BY option_name")
            OPTIONS_LIST = ["Toutes les options"] + [row[0] for row in cursor.fetchall()]

        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM pr_after_reform26 ORDER BY name")
            PROVINCES_26 = [row[0] for row in cursor.fetchall()]
    finally:
        try:
            conn.close()
        except Exception:
            pass
except Exception as exc:
    # If the DB is unavailable at import time, provide safe defaults so the
    # dashboard can still be imported and unit-tested without a running DB.
    print("Warning: exetat_dashboard.config could not initialize from DB:", exc)
    AVAILABLE_YEARS = []
    DEFAULT_YEAR = 2023
    DEFAULT_OPTION = "Toutes les options"
    OPTIONS_LIST = [DEFAULT_OPTION]
    PROVINCES_26 = []

# ---------------------------------------------------------------------------
# Theme — national education intelligence / command-center palette
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#00A8FF",
    "primary_dark": "#00E5FF",
    "primary_light": "#102A42",
    "success": "#00D68F",
    "danger": "#FF5C7A",
    "text": "#EAF6FF",
    "muted": "#7893AA",
    "bg": "#050B16",
    "card_bg": "#0C1728",
    "border": "#1A3952",
}

# Choropleth colorscale — light lavender to deep indigo/purple (darker = higher rate)
MAP_COLORSCALE = [
    [0.0, "#102A42"],
    [0.25, "#075985"],
    [0.5, "#0284C7"],
    [0.75, "#00A8FF"],
    [1.0, "#00E5FF"],
]

# Buckets for the "Success Rate by Range" donut — keep in sync with any
# GROUP BY / CASE WHEN bucketing you do in queries/province.py
SUCCESS_RATE_BUCKETS = [
    {"label": "Excellent (≥ 0.31)", "min": 0.31, "max": 1.01, "color": "#00E5FF"},
    {"label": "Good (0.27 – 0.31)", "min": 0.27, "max": 0.31, "color": "#00A8FF"},
    {"label": "Average (0.23 – 0.27)", "min": 0.23, "max": 0.27, "color": "#38BDF8"},
    {"label": "Low (0.19 – 0.23)", "min": 0.19, "max": 0.23, "color": "#FFC857"},
    {"label": "Very Low (≤ 0.19)", "min": 0.0, "max": 0.19, "color": "#FF5C7A"},
]

STUDENT_PERCENTAGE_BUCKETS = [
    {"label": "50-59%", "color": "#1E4B6A"},
    {"label": "60-69%", "color": "#075985"},
    {"label": "70-79%", "color": "#0284C7"},
    {"label": "80-89%", "color": "#00A8FF"},
    {"label": "90%+", "color": "#00E5FF"},
]
