"""Shared database access and parameterized filter helpers."""
import pandas as pd

import logging

logger = logging.getLogger(__name__)


class QueryError(RuntimeError):
    """A database read failed; details belong in server logs, never in the UI."""


def get_connection():
    # Keep the host project's connection implementation; importing this lazily
    # lets Dash render an empty state if the external database package is absent.
    from database.db import get_connection as connect
    return connect()



def _read_sql(query: str, params=None, default=None, *, raise_on_error=False):
    try:
        conn = get_connection()
        try:
            return pd.read_sql(query, con=conn, params=params)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Database read failed (%s)", type(exc).__name__)
        if raise_on_error:
            raise QueryError("Data is temporarily unavailable. Please try again.") from exc
        return default


def _build_option_clause(option: str | None):
    if option in (None, "", "Toutes les options"):
        return "", ()
    return " AND o.option_name = %s", (option,)


def _build_province_clause(province: str | None, alias: str = "p26"):
    """Optional AND clause filtering on the post-reform (26) province name.

    Only usable in queries that already JOIN pr_after_reform26 (aliased as
    `alias`, default 'p26') — see queries/province.py and
    queries/overview.py for the join pattern
    (schools -> educational_province -> pr_after_reform26).
    """
    if province in (None, "", "Toutes les provinces"):
        return "", ()
    return f" AND {alias}.name = %s", (province,)
