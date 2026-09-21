"""Bounded school lookup and rankings using the existing session relationships."""
from exetat_dashboard.queries.analytics import (
    page_bounds, read_frame, school_rates_sql, student_results_cte,
)


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
