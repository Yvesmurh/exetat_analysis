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
# Theme — DRC Government-inspired Education Intelligence Palette
# ---------------------------------------------------------------------------
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONT_MONO = "'IBM Plex Mono', monospace"

COLORS = {
    "primary": "#007FFF",         # Government blue
    "primary_dark": "#0056B3",    # Deep blue
    "primary_light": "#EBF5FF",   # Soft blue tint
    "navy": "#071A33",            # Deep navy
    "flag_red": "#CE1021",        # Flag red
    "flag_yellow": "#F7D116",     # Flag yellow
    "success": "#10B981",         # Emerald green
    "danger": "#CE1021",          # Red
    "warning": "#F59E0B",         # Amber
    "text": "#071A33",            # Deep navy text (high contrast)
    "text_secondary": "#334155",  # Slate-700 (high contrast WCAG AAA)
    "muted": "#475569",           # Slate-600 (strong legible contrast)
    "bg": "#F3F6FA",              # Light executive background
    "card_bg": "#FFFFFF",         # Pure white cards
    "border": "#E2E8F0",          # Crisp light border
}

# Choropleth colorscale — light sky blue to deep government navy (darker = higher rate)
MAP_COLORSCALE = [
    [0.0, "#E0F2FE"],
    [0.25, "#7DD3FC"],
    [0.5, "#38BDF8"],
    [0.75, "#007FFF"],
    [1.0, "#071A33"],
]

# Buckets for the "Success Rate by Range" donut
SUCCESS_RATE_BUCKETS = [
    {"label": "Excellent (≥ 0.31)", "min": 0.31, "max": 1.01, "color": "#007FFF"},
    {"label": "Good (0.27 – 0.31)", "min": 0.27, "max": 0.31, "color": "#0284C7"},
    {"label": "Average (0.23 – 0.27)", "min": 0.23, "max": 0.27, "color": "#38BDF8"},
    {"label": "Low (0.19 – 0.23)", "min": 0.19, "max": 0.23, "color": "#F59E0B"},
    {"label": "Very Low (≤ 0.19)", "min": 0.0, "max": 0.19, "color": "#CE1021"},
]

STUDENT_PERCENTAGE_BUCKETS = [
    {"label": "50-59%", "color": "#93C5FD"},
    {"label": "60-69%", "color": "#38BDF8"},
    {"label": "70-79%", "color": "#0284C7"},
    {"label": "80-89%", "color": "#007FFF"},
    {"label": "90%+", "color": "#071A33"},
]
