import pandas as pd

from exetat_dashboard.config import STUDENT_PERCENTAGE_BUCKETS, SUCCESS_RATE_BUCKETS
from exetat_dashboard.queries.helpers import _build_option_clause, _read_sql

"""
Queries powering the choropleth map, the province ranking list, and the
student percentage distribution pie.
"""


def get_province_stats(year: int, option: str | None = None):
    """
    One row per province (26 rows), sorted by rank ascending.

    Returns
    -------
    pandas.DataFrame with columns:
        province (str)              # uppercase French, matches GeoJSON join key
        success_rate (float)        # 0-1
        schools (int)
        participants (int)
        delta_vs_prev_year (float)  # percentage points
        rank (int)
    """
    option_clause, option_params = _build_option_clause(option)

    # NOTE: aggregate by the post-reform province (p26.id), not by
    # educational_province.id / s.province_id. Several pre-reform
    # educational_province rows can map to the same post-reform province
    # (pr_after_reform26) — grouping by s.province_id produced duplicate
    # rows for the same province name (e.g. two "KINSHASA" rows), which
    # broke the choropleth join and double-counted it in the ranking.
    query = f"""
        WITH current_year AS (
            SELECT
                p26.id AS province_after_id,
                p26.name AS province,
                COALESCE(SUM(ee.reussites), 0) AS successes,
                COALESCE(SUM(ee.participants), 0) AS participants,
                COUNT(DISTINCT s.id) AS schools
            FROM exetat_entry ee
            JOIN schools s ON s.id = ee.school_id
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            LEFT JOIN options o ON o.id = ee.option_id
            WHERE ee.years = %s{option_clause}
            GROUP BY p26.id, p26.name
        ),
        previous_year AS (
            SELECT
                p26.id AS province_after_id,
                COALESCE(SUM(ee.reussites), 0) AS prev_successes,
                COALESCE(SUM(ee.participants), 0) AS prev_participants
            FROM exetat_entry ee
            JOIN schools s ON s.id = ee.school_id
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            LEFT JOIN options o ON o.id = ee.option_id
            WHERE ee.years = %s{option_clause}
            GROUP BY p26.id
        )
        SELECT
            c.province,
            c.successes,
            c.successes / NULLIF(c.participants, 0) AS success_rate,
            c.schools,
            c.participants,
            CASE
                WHEN p.prev_participants > 0 THEN (
                    (c.successes / NULLIF(c.participants, 0)) -
                    (p.prev_successes / NULLIF(p.prev_participants, 0))
                ) * 100
                ELSE NULL
            END AS delta_vs_prev_year
        FROM current_year c
        LEFT JOIN previous_year p ON p.province_after_id = c.province_after_id
        ORDER BY c.province
    """

    df = _read_sql(
        query,
        (year, *option_params, year - 1, *option_params),
        default=pd.DataFrame(columns=["province", "successes", "success_rate", "schools", "participants", "delta_vs_prev_year"]),
    )

    columns = ["province", "successes", "success_rate", "schools", "participants", "delta_vs_prev_year", "rank"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df["successes"] = pd.to_numeric(df["successes"], errors="coerce").fillna(0).astype(int)
    df["success_rate"] = pd.to_numeric(df["success_rate"], errors="coerce").fillna(0.0)
    df["schools"] = pd.to_numeric(df["schools"], errors="coerce").fillna(0).astype(int)
    df["participants"] = pd.to_numeric(df["participants"], errors="coerce").fillna(0).astype(int)
    df["delta_vs_prev_year"] = pd.to_numeric(df["delta_vs_prev_year"], errors="coerce")

    df = df.sort_values(["success_rate", "province"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df[columns]


def get_success_rate_distribution(year: int, option: str | None = None):
    """
    Count of provinces per success-rate bucket, for the donut chart.
    See config.SUCCESS_RATE_BUCKETS for the bucket boundaries — bucket this
    with a SQL CASE WHEN or in pandas after get_province_stats().

    Returns
    -------
    pandas.DataFrame with columns: bucket_label (str), province_count (int)
    """
    option_clause, option_params = _build_option_clause(option)
    query = f"""
        WITH province_rates AS (
            SELECT
                p26.name AS province,
                SUM(ee.reussites) / NULLIF(SUM(ee.participants), 0) AS success_rate
            FROM exetat_entry ee
            JOIN schools s ON s.id = ee.school_id
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            LEFT JOIN options o ON o.id = ee.option_id
            WHERE ee.years = %s{option_clause}
            GROUP BY p26.name
        )
        SELECT
            CASE
                WHEN success_rate >= 0.31 THEN 'Excellent (≥ 0.31)'
                WHEN success_rate >= 0.27 THEN 'Good (0.27 – 0.31)'
                WHEN success_rate >= 0.23 THEN 'Average (0.23 – 0.27)'
                WHEN success_rate >= 0.19 THEN 'Low (0.19 – 0.23)'
                ELSE 'Very Low (≤ 0.19)'
            END AS bucket_label,
            COUNT(*) AS province_count
        FROM province_rates
        GROUP BY bucket_label
    """

    df = _read_sql(
        query,
        (year, *option_params),
        default=pd.DataFrame(columns=["bucket_label", "province_count"]),
    )

    label_order = [bucket["label"] for bucket in SUCCESS_RATE_BUCKETS]
    if df.empty:
        df = pd.DataFrame({"bucket_label": label_order, "province_count": [0] * len(label_order)})
    else:
        df["bucket_label"] = df["bucket_label"].astype(str)
        df["province_count"] = pd.to_numeric(df["province_count"], errors="coerce").fillna(0).astype(int)
        indexed = df.set_index("bucket_label").reindex(label_order).fillna(0).reset_index()
        indexed.columns = ["bucket_label", "province_count"]
        df = indexed

    return df[["bucket_label", "province_count"]]


def get_student_percentage_distribution(year: int, option: str | None = None):
    """Count valid students in each percentage band for a given year."""
    option_clause, option_params = _build_option_clause(option)
    query = f"""
        SELECT
            CASE
                WHEN r.percentage >= 90 THEN '90%+'
                WHEN r.percentage >= 80 THEN '80-89%'
                WHEN r.percentage >= 70 THEN '70-79%'
                WHEN r.percentage >= 60 THEN '60-69%'
                WHEN r.percentage >= 50 THEN '50-59%'
            END AS bucket_label,
            COUNT(*) AS student_count
        FROM exam_results r
        JOIN students st ON st.id = r.student_id
        JOIN exetat_entry e ON e.id = r.school_session_id
        LEFT JOIN options o ON o.id = e.option_id
        WHERE e.years = %s
          AND st.student_name NOT REGEXP '^[0-9]'{option_clause}
          AND r.percentage >= 50
        GROUP BY bucket_label
    """

    df = _read_sql(
        query,
        (year, *option_params),
        default=pd.DataFrame(columns=["bucket_label", "student_count"]),
    )

    label_order = [bucket["label"] for bucket in STUDENT_PERCENTAGE_BUCKETS]
    if df.empty:
        return pd.DataFrame({"bucket_label": label_order, "student_count": [0] * len(label_order)})

    df["bucket_label"] = df["bucket_label"].astype(str)
    df["student_count"] = pd.to_numeric(df["student_count"], errors="coerce").fillna(0).astype(int)
    return (
        df.set_index("bucket_label")
        .reindex(label_order, fill_value=0)
        .reset_index()[["bucket_label", "student_count"]]
    )
