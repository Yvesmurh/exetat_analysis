"""Shared province/school aggregations. Rates here use 0–100 units.

Session totals must never join exam_results: that would multiply participants
by the number of recorded students. Missing denominators produce NULL, not 0%.
The schema follows the existing working queries, not legacy TODO notes.
"""
import pandas as pd
from exetat_dashboard.queries.helpers import _build_option_clause, _build_province_clause, _read_sql

SESSION_JOINS = """
    FROM exetat_entry ee
    JOIN schools s ON s.id = ee.school_id
    JOIN educational_province ep ON ep.id = s.province_id
    JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
    LEFT JOIN options o ON o.id = ee.option_id
"""
TREND_YEARS = list(range(2015, 2024))
BAND_LABELS = ["90%+", "80–<90%", "70–<80%", "60–<70%", "50–<60%", "Below 50%"]


def scope_clause(province, option=None, school_id=None):
    """A cleared province must never widen the query to the whole nation."""
    province_clause, province_params = _build_province_clause(province)
    if not province_clause:
        return " AND 1 = 0", ()
    option_clause, option_params = _build_option_clause(option)
    school_clause = " AND ee.school_id = %s" if school_id is not None else ""
    school_params = (int(school_id),) if school_id is not None else ()
    return (province_clause + option_clause + school_clause,
            (*province_params, *option_params, *school_params))


def read_frame(query, params, columns):
    return _read_sql(query, params, default=pd.DataFrame(columns=columns), raise_on_error=True)


def get_scope_overview(province, year, option=None, school_id=None):
    if not province or year is None:
        return {}
    clause, params = scope_clause(province, option, school_id)
    df = read_frame(f"""
        SELECT ee.years AS year, COUNT(*) AS session_count,
               COUNT(DISTINCT ee.school_id) AS total_schools,
               COUNT(DISTINCT ee.option_id) AS total_options,
               COALESCE(SUM(ee.participants), 0) AS total_participants,
               COALESCE(SUM(ee.reussites), 0) AS total_successful,
               100.0 * SUM(ee.reussites) / NULLIF(SUM(ee.participants), 0) AS success_rate
        {SESSION_JOINS}
        WHERE ee.years IN (%s, %s){clause}
        GROUP BY ee.years
    """, (int(year), int(year) - 1, *params),
        ["year", "session_count", "total_schools", "total_options",
         "total_participants", "total_successful", "success_rate"])
    current = df.loc[df["year"] == int(year)]
    if current.empty:
        return {}
    result = current.iloc[0].to_dict()
    previous = df.loc[df["year"] == int(year) - 1, "success_rate"]
    prev_rate = previous.iloc[0] if not previous.empty else None
    rate = result["success_rate"]
    result["success_rate"] = None if pd.isna(rate) else float(rate)
    result["previous_success_rate"] = None if pd.isna(prev_rate) else float(prev_rate)
    result["success_rate_delta_vs_prev_year"] = (
        None if result["success_rate"] is None or result["previous_success_rate"] is None
        else round(result["success_rate"] - result["previous_success_rate"], 2)
    )
    return result


def get_scope_trend(province, option=None, school_id=None):
    clause, params = scope_clause(province, option, school_id)
    return read_frame(f"""
        SELECT ee.years AS year,
               100.0 * SUM(ee.reussites) / NULLIF(SUM(ee.participants), 0) AS success_rate
        {SESSION_JOINS}
        WHERE ee.years BETWEEN %s AND %s{clause}
        GROUP BY ee.years ORDER BY ee.years
    """, (TREND_YEARS[0], TREND_YEARS[-1], *params), ["year", "success_rate"])


def school_rates_sql(province, year, option=None):
    clause, params = scope_clause(province, option)
    return f"""
        SELECT s.id AS school_id, s.school_name,
               COALESCE(SUM(ee.participants), 0) AS participants,
               COALESCE(SUM(ee.reussites), 0) AS successes,
               100.0 * SUM(ee.reussites) / NULLIF(SUM(ee.participants), 0) AS success_rate
        {SESSION_JOINS}
        WHERE ee.years = %s{clause}
        GROUP BY s.id, s.school_name
    """, (year, *params)


def student_results_cte(province, school_id, year, option=None):
    """One observation per student ID within the selected school/year.

    Repeated result rows cannot duplicate a student. If a student ID has several
    sessions/options in the selection, retain its best recorded score, breaking
    ties by option and session ID. Never deduplicate people by their names.
    Ranking and distribution consume exactly the same result population.
    """
    clause, params = scope_clause(province, option, school_id)
    if school_id is None:
        clause += " AND 1 = 0"
    return f"""
        WITH scoped_results AS (
            SELECT st.id AS student_id, st.student_name,
                   o.option_name, er.percentage,
                   ROW_NUMBER() OVER (
                       PARTITION BY st.id
                       ORDER BY er.percentage DESC, ee.option_id, ee.id
                   ) AS result_number
            {SESSION_JOINS}
            JOIN exam_results er ON er.school_session_id = ee.id
            JOIN students st ON st.id = er.student_id
            WHERE ee.years = %s{clause}
              AND er.percentage BETWEEN 0 AND 100
        ), student_scores AS (
            SELECT student_id, student_name, option_name, percentage
            FROM scoped_results WHERE result_number = 1
        )
    """, (year, *params)


def distribution_sql(source, value_column):
    # Identifiers are internal constants from the two call sites, never input.
    return f"""
        SELECT CASE
            WHEN {value_column} >= 90 THEN %s
            WHEN {value_column} >= 80 THEN %s
            WHEN {value_column} >= 70 THEN %s 
            WHEN {value_column} >= 60 THEN %s
            WHEN {value_column} >= 50 THEN %s
            ELSE %s END AS bucket_label,
            COUNT(*) AS item_count
        FROM {source}
        WHERE {value_column} BETWEEN 0 AND 100
        GROUP BY bucket_label
    """


def ordered_distribution(query, params):
    df = read_frame(query, (*params, *BAND_LABELS), ["bucket_label", "item_count"])
    return df.set_index("bucket_label").reindex(BAND_LABELS, fill_value=0).reset_index()


def get_school_rate_distribution(province, year, option=None):
    query, params = school_rates_sql(province, year, option)
    return ordered_distribution(
        f"WITH school_rates AS ({query}) " + distribution_sql("school_rates", "success_rate"), params)


def get_school_student_distribution(province, school_id, year, option=None):
    cte, params = student_results_cte(province, school_id, year, option)
    return ordered_distribution(cte + distribution_sql("student_scores", "percentage"), params)


def page_bounds(limit, offset):
    """At most 51 rows (50 displayed + a next-page sentinel) per SQL read."""
    return min(51, max(1, int(limit))), max(0, int(offset))
