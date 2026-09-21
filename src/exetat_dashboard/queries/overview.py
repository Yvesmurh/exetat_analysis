import pandas as pd
from exetat_dashboard.queries.helpers import _build_option_clause, _build_province_clause, _read_sql

"""
Queries for the national overview cards (top-left column of the home page).

Wire these up to MySQL however you prefer (mysql-connector, SQLAlchemy,
pandas.read_sql...). Everything downstream (figures/overview_cards.py) only
cares about the dict shapes documented below.
"""


def get_national_overview(year: int, option: str | None = None, province: str | None = None) -> dict:
    """
    Returns
    -------
    dict with keys:
        total_schools: int
        total_participants: int
        total_successful: int
        success_rate: float                     # 0-100
        success_rate_delta_vs_prev_year: float   # percentage points
    """
    option_clause, option_params = _build_option_clause(option)
    province_clause, province_params = _build_province_clause(province)
    # province_clause references p26.name — only join that chain when a
    # province filter is actually requested, to avoid the extra join cost
    # on the (much more common) "all provinces" case.
    province_join = (
        " JOIN educational_province ep ON ep.id = s.province_id"
        " JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id"
        if province_clause
        else ""
    )

    current_query = f"""
        SELECT
            COUNT(DISTINCT ee.school_id) AS total_schools,
            COALESCE(SUM(ee.participants), 0) AS total_participants,
            COALESCE(SUM(ee.reussites), 0) AS total_successful
        FROM exetat_entry ee
        JOIN schools s ON s.id = ee.school_id
        LEFT JOIN options o ON o.id = ee.option_id{province_join}
        WHERE ee.years = %s{option_clause}{province_clause}
    """
    current_df = _read_sql(
        current_query,
        (year, *option_params, *province_params),
        default=pd.DataFrame([{"total_schools": 0, "total_participants": 0, "total_successful": 0}]),
    )

    prev_query = f"""
        SELECT
            COALESCE(SUM(ee.participants), 0) AS prev_participants,
            COALESCE(SUM(ee.reussites), 0) AS prev_successful
        FROM exetat_entry ee
        JOIN schools s ON s.id = ee.school_id
        LEFT JOIN options o ON o.id = ee.option_id{province_join}
        WHERE ee.years = %s{option_clause}{province_clause}
    """
    prev_df = _read_sql(
        prev_query,
        (year - 1, *option_params, *province_params),
        default=pd.DataFrame([{"prev_participants": 0, "prev_successful": 0}]),
    )

    row = current_df.iloc[0] if not current_df.empty else None
    prev_row = prev_df.iloc[0] if not prev_df.empty else None

    if row is None:
        return {
            "total_schools": 0,
            "total_participants": 0,
            "total_successful": 0,
            "success_rate": 0.0,
            "success_rate_delta_vs_prev_year": None,
        }

    total_participants = int(row.get("total_participants", 0) or 0)
    total_successful = int(row.get("total_successful", 0) or 0)
    success_rate = (total_successful / total_participants * 100) if total_participants else 0.0

    prev_participants = int(prev_row.get("prev_participants", 0) or 0) if prev_row is not None else 0
    prev_successful = int(prev_row.get("prev_successful", 0) or 0) if prev_row is not None else 0
    prev_rate = (prev_successful / prev_participants * 100) if prev_participants else None
    delta = None if prev_rate is None else success_rate - prev_rate

    return {
        "total_schools": int(row.get("total_schools", 0) or 0),
        "total_participants": total_participants,
        "total_successful": total_successful,
        "success_rate": round(success_rate, 2),
        "success_rate_delta_vs_prev_year": round(delta, 2) if delta is not None else None,
    }


def get_top_performing_student(year: int, option: str | None = None) -> dict:
    """Return the top performing student for the requested year and option."""
    option_clause, option_params = _build_option_clause(option)

    query = f"""
        SELECT
            st.student_name,
            s.school_name,
            ep.name AS province,
            er.percentage
        FROM exam_results er
        JOIN students st ON st.id = er.student_id
        JOIN exetat_entry ee ON ee.id = er.school_session_id
        JOIN schools s ON s.id = ee.school_id
        JOIN educational_province ep ON ep.id = s.province_id
        LEFT JOIN options o ON o.id = ee.option_id
        WHERE ee.years = %s{option_clause}
        ORDER BY er.percentage DESC, st.student_name
        LIMIT 1
    """
    df = _read_sql(
        query,
        (year, *option_params),
        default=pd.DataFrame([{"student_name": None, "school_name": None, "province": None, "percentage": 0.0}]),
    )

    if df.empty:
        return {
            "student_name": None,
            "school_name": None,
            "province": None,
            "percentage": 0.0,
        }

    row = df.iloc[0]
    return {
        "student_name": row["student_name"],
        "school_name": row["school_name"],
        "province": row["province"],
        "percentage": round(float(row["percentage"] or 0.0), 2),
    }


def get_top_students_by_option(year: int, option: str | None = None, province: str | None = None,
                               school_id: int | None = None, *,
                               raise_on_error: bool = False) -> pd.DataFrame:
    """
    Both current and previous CTEs use the same province/school scope.
    Ties resolve by name, student ID, then session ID.
    Top performing student for each educational option, for the selected
    year, compared against the best percentage for that same option the
    previous year. Powers the "Top Performing Students" table on the home
    page (replaces the old "Top Performing Province" card).

    Returns
    -------
    pandas.DataFrame with columns:
        option_name (str)
        top_student_current (str)
        top_percentage_current (float)   # 0-100
        top_percentage_previous (float)  # 0-100, NaN if no prior-year data
        pts_change (float)               # NaN if no prior-year data
    """
    option_clause, option_params = _build_option_clause(option)
    province_clause, province_params = _build_province_clause(province)
    province_join = (
        " JOIN educational_province ep ON ep.id = s.province_id"
        " JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id"
        if province_clause
        else ""
    )

    school_clause = " AND ee.school_id = %s" if school_id is not None else ""
    school_params = (school_id,) if school_id is not None else ()

    query = f"""
        WITH ranked_current AS (
            SELECT
                o.id AS option_id,
                o.option_name,
                st.student_name,
                er.percentage,
                ROW_NUMBER() OVER (
                    PARTITION BY o.id
                    ORDER BY er.percentage DESC, st.student_name, st.id, ee.id
                ) AS rn
            FROM exam_results er
            JOIN exetat_entry ee ON ee.id = er.school_session_id
            JOIN options o ON o.id = ee.option_id
            JOIN students st ON st.id = er.student_id
            JOIN schools s ON s.id = ee.school_id{province_join}
            WHERE ee.years = %s{option_clause}{province_clause}{school_clause}
              AND er.percentage BETWEEN 0 AND 100
        ),
        top_previous AS (
            SELECT
                o.id AS option_id,
                MAX(er.percentage) AS top_percentage_previous
            FROM exam_results er
            JOIN exetat_entry ee ON ee.id = er.school_session_id
            JOIN options o ON o.id = ee.option_id
            JOIN schools s ON s.id = ee.school_id{province_join}
            WHERE ee.years = %s{option_clause}{province_clause}{school_clause}
              AND er.percentage BETWEEN 0 AND 100
            GROUP BY o.id
        )
        SELECT
            r.option_name,
            r.student_name AS top_student_current,
            r.percentage AS top_percentage_current,
            p.top_percentage_previous,
            ROUND(r.percentage - p.top_percentage_previous, 2) AS pts_change
        FROM ranked_current r
        LEFT JOIN top_previous p ON p.option_id = r.option_id
        WHERE r.rn = 1
        ORDER BY r.percentage DESC
    """
    df = _read_sql(
        query,
        (year, *option_params, *province_params, *school_params,
         year - 1, *option_params, *province_params, *school_params),
        raise_on_error=raise_on_error,
        default=pd.DataFrame(
            columns=["option_name", "top_student_current", "top_percentage_current", "top_percentage_previous", "pts_change"]
        ),
    )
    if df.empty:
        return df

    df["top_percentage_current"] = pd.to_numeric(df["top_percentage_current"], errors="coerce").fillna(0.0)
    df["top_percentage_previous"] = pd.to_numeric(df["top_percentage_previous"], errors="coerce")
    df["pts_change"] = pd.to_numeric(df["pts_change"], errors="coerce")
    return df
