import pandas as pd

from exetat_dashboard.queries.helpers import _build_option_clause, _read_sql

"""
Query powering the "Province Performance Trend" sparkline row.
"""


def get_province_trends(provinces: list[str], years: list[int], option: str | None = None):
    """
    Yearly success-rate series for each of the given provinces (one
    sparkline per province on the home page).

    Returns
    -------
    pandas.DataFrame with columns:
        province (str), year (int), success_rate (float, 0-1)
    Sorted by province, then year.
    """
    if not provinces or not years:
        return pd.DataFrame(columns=["province", "year", "success_rate"])

    province_placeholders = ", ".join(["%s"] * len(provinces))
    year_placeholders = ", ".join(["%s"] * len(years))
    option_clause, option_params = _build_option_clause(option)
    params = list(provinces) + list(years) + list(option_params)

    query = f"""
        SELECT
            p26.name AS province,
            ee.years AS year,
            SUM(ee.reussites) / NULLIF(SUM(ee.participants), 0) AS success_rate
        FROM exetat_entry ee
        JOIN schools s ON s.id = ee.school_id
        JOIN educational_province ep ON ep.id = s.province_id
        JOIN pr_after_reform26 p26 ON p26.id = ep.province_after_id
        LEFT JOIN options o ON o.id = ee.option_id
        WHERE p26.name IN ({province_placeholders})
          AND ee.years IN ({year_placeholders}){option_clause}
        GROUP BY p26.name, ee.years
        ORDER BY p26.name, ee.years
    """
    df = _read_sql(
        query,
        tuple(params),
        default=pd.DataFrame(columns=["province", "year", "success_rate"]),
    )
    if df.empty:
        return df
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["success_rate"] = pd.to_numeric(df["success_rate"], errors="coerce").fillna(0.0)
    return df[["province", "year", "success_rate"]].sort_values(["province", "year"]).reset_index(drop=True)