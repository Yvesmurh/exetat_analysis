"""Bounded school lookup, student discovery, and institutional history using MySQL."""
import pandas as pd
from exetat_dashboard.queries.analytics import (
    page_bounds, read_frame, school_rates_sql, student_results_cte,
)
from exetat_dashboard.queries.helpers import _read_sql


def get_school_choices(province, search="", selected_id=None):
    """Up to 50 province-local matches, retaining a valid selected school.

    IDs disambiguate identical names. A selection outside this province cannot
    be retained. LOCATE treats %, _ and quotes as literal search characters.
    """
    if not province:
        return []
    search = str(search or "").strip()[:150]
    selected_id = int(selected_id) if selected_id is not None else None
    query = """
        WITH matches AS (
            SELECT s.id AS school_id, s.school_name
            FROM schools s
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            WHERE p26.name = %s AND (%s = '' OR LOCATE(%s, s.school_name) > 0)
            ORDER BY s.school_name, s.id LIMIT 50
        ), selected AS (
            SELECT s.id AS school_id, s.school_name
            FROM schools s
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            WHERE p26.name = %s AND s.id = %s
        )
        SELECT school_id, school_name FROM matches
        UNION
        SELECT school_id, school_name FROM selected
        ORDER BY school_name, school_id
    """
    df = read_frame(query, (province, search, search, province, selected_id), ["school_id", "school_name"])
    return [{"label": f"{row.school_name} · #{int(row.school_id)}", "value": int(row.school_id)}
            for row in df.itertuples()]


def get_schools(province=None, year=None, option=None, limit=11, offset=0):
    """Weighted school ranking, 0–100 rate; undefined rates sort last.

    Grouping by school ID/name prevents counting each option as a school.
    Rate = SUM(reussites)/SUM(participants), never AVG(percentages).
    Stable ID tie-breaking prevents overlaps between unchanged result pages.
    """
    query, params = school_rates_sql(province, year, option)
    limit, offset = page_bounds(limit, offset)
    df = read_frame(f"""
        {query}
        ORDER BY (success_rate IS NULL), success_rate DESC, school_name, school_id
        LIMIT %s OFFSET %s
    """, (*params, limit, offset),
        ["school_id", "school_name", "participants", "successes", "success_rate"])
    df["rank"] = range(offset + 1, offset + len(df) + 1)
    return df


def get_student_ranking(province, school_id, year, option=None, limit=11, offset=0):
    cte, params = student_results_cte(province, school_id, year, option)
    limit, offset = page_bounds(limit, offset)
    df = read_frame(f"""
        {cte}
        SELECT student_id, student_name, option_name, percentage
        FROM student_scores
        ORDER BY percentage DESC, student_name, student_id
        LIMIT %s OFFSET %s
    """, (*params, limit, offset), ["student_id", "student_name", "option_name", "percentage"])
    df["rank"] = range(offset + 1, offset + len(df) + 1)
    return df


# ---------------------------------------------------------------------------
# Student-centered discovery queries (MySQL)
# ---------------------------------------------------------------------------

def search_students(student_name: str, exam_year: int, limit: int = 50) -> pd.DataFrame:
    """Search for former EXETAT students by full or partial name and graduation year."""
    if not student_name or not str(student_name).strip() or exam_year is None:
        return pd.DataFrame()

    name_pattern = f"%{str(student_name).strip()}%"
    query = """
        WITH ranked_matches AS (
            SELECT
                st.id AS student_id,
                st.student_name,
                st.student_code,
                st.sexe,
                s.id AS school_id,
                s.school_name,
                s.school_code,
                p26.name AS province_name,
                ee.years AS exam_year,
                o.id AS option_id,
                o.option_name,
                er.percentage,
                ROW_NUMBER() OVER (
                    PARTITION BY st.id, ee.years
                    ORDER BY er.percentage DESC, ee.id ASC
                ) AS rn
            FROM students st
            JOIN exam_results er ON er.student_id = st.id
            JOIN exetat_entry ee ON ee.id = er.school_session_id
            JOIN schools s ON s.id = ee.school_id
            JOIN educational_province ep ON ep.id = s.province_id
            JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
            JOIN options o ON o.id = ee.option_id
            WHERE ee.years = %s
              AND LOWER(st.student_name) LIKE LOWER(%s)
        )
        SELECT
            student_id, student_name, student_code, sexe,
            school_id, school_name, school_code, province_name,
            exam_year, option_id, option_name, percentage
        FROM ranked_matches
        WHERE rn = 1
        ORDER BY student_name ASC, percentage DESC
        LIMIT %s
    """
    cols = [
        "student_id", "student_name", "student_code", "sexe",
        "school_id", "school_name", "school_code", "province_name",
        "exam_year", "option_id", "option_name", "percentage",
    ]
    return _read_sql(query, params=(int(exam_year), name_pattern, int(limit)), default=pd.DataFrame(columns=cols))


def get_school_classmates(school_id: int, exam_year: int, search_filter: str = "") -> pd.DataFrame:
    """Retrieve all classmates from the same school and examination year with rankings."""
    if school_id is None or exam_year is None:
        return pd.DataFrame()

    query = """
        WITH classmates AS (
            SELECT
                st.id AS student_id,
                st.student_name,
                o.option_name,
                er.percentage,
                ROW_NUMBER() OVER (
                    PARTITION BY st.id
                    ORDER BY er.percentage DESC, ee.id ASC
                ) AS rn
            FROM students st
            JOIN exam_results er ON er.student_id = st.id
            JOIN exetat_entry ee ON ee.id = er.school_session_id
            JOIN options o ON o.id = ee.option_id
            WHERE ee.school_id = %s
              AND ee.years = %s
              AND er.percentage BETWEEN 0 AND 100
        )
        SELECT student_id, student_name, option_name, percentage
        FROM classmates
        WHERE rn = 1
        ORDER BY percentage DESC, student_name ASC
    """
    cols = ["student_id", "student_name", "option_name", "percentage"]
    df = _read_sql(query, params=(int(school_id), int(exam_year)), default=pd.DataFrame(columns=cols))
    if df is not None and not df.empty:
        df["rank"] = range(1, len(df) + 1)
        if search_filter and str(search_filter).strip():
            clean_search = str(search_filter).strip().lower()
            df = df[df["student_name"].str.lower().str.contains(clean_search, na=False)]
    return df


def get_school_options_summary(school_id: int, exam_year: int) -> pd.DataFrame:
    """Retrieve all educational options offered at the school in that year with outcomes."""
    if school_id is None or exam_year is None:
        return pd.DataFrame()

    query = """
        SELECT
            o.id AS option_id,
            o.option_name,
            COALESCE(ee.participants, 0) AS participants,
            COALESCE(ee.reussites, 0) AS successes,
            CASE
                WHEN ee.participants > 0 THEN ROUND(100.0 * ee.reussites / ee.participants, 2)
                ELSE NULL
            END AS success_rate
        FROM exetat_entry ee
        JOIN options o ON o.id = ee.option_id
        WHERE ee.school_id = %s
          AND ee.years = %s
        ORDER BY success_rate DESC, o.option_name ASC
    """
    cols = ["option_id", "option_name", "participants", "successes", "success_rate"]
    return _read_sql(query, params=(int(school_id), int(exam_year)), default=pd.DataFrame(columns=cols))


def get_school_history_5years(school_id: int, end_year: int) -> pd.DataFrame:
    """Retrieve school performance for 5 years leading up to and including end_year.

    Gaps/missing years are preserved with None values (never interpolated or estimated).
    """
    if school_id is None or end_year is None:
        return pd.DataFrame()

    start_year = int(end_year) - 4
    years_range = list(range(start_year, int(end_year) + 1))

    query = """
        SELECT
            ee.years AS year,
            COALESCE(SUM(ee.participants), 0) AS participants,
            COALESCE(SUM(ee.reussites), 0) AS successes,
            CASE
                WHEN SUM(ee.participants) > 0 THEN ROUND(100.0 * SUM(ee.reussites) / SUM(ee.participants), 2)
                ELSE NULL
            END AS success_rate
        FROM exetat_entry ee
        WHERE ee.school_id = %s
          AND ee.years BETWEEN %s AND %s
        GROUP BY ee.years
        ORDER BY ee.years ASC
    """
    cols = ["year", "participants", "successes", "success_rate"]
    df = _read_sql(query, params=(int(school_id), start_year, int(end_year)), default=pd.DataFrame(columns=cols))

    if df is not None:
        if not df.empty and "year" in df.columns:
            df["year"] = df["year"].astype(int)
            df = df.set_index("year").reindex(years_range).reset_index()
        else:
            df = pd.DataFrame({
                "year": years_range,
                "participants": [None] * len(years_range),
                "successes": [None] * len(years_range),
                "success_rate": [None] * len(years_range),
            })
    return df
