"""Small shared rendering and paging helpers; no SQL or database connections."""
import logging
from exetat_dashboard.figures.analytics import empty_state, empty_figure, build_detail_ranking
from exetat_dashboard.queries.helpers import QueryError

logger = logging.getLogger(__name__)
ERROR_MESSAGE = "Data is temporarily unavailable. Please try again."


def safe_render(loader, builder, figure=False):
    """A failure in one section must not prevent the other sections rendering."""
    try:
        return builder(loader())
    except QueryError:
        return empty_figure(ERROR_MESSAGE) if figure else empty_state(ERROR_MESSAGE)
    except Exception:
        logger.exception("Analytics component failed to render")
        return empty_figure(ERROR_MESSAGE) if figure else empty_state(ERROR_MESSAGE)


def next_paging_state(previous, selection, trigger, prefix):
    previous = previous or {}
    state = {"selection": selection, "expanded": False, "page": 0, "has_next": False}
    if previous.get("selection") != selection:
        return state
    state["expanded"] = bool(previous.get("expanded"))
    state["page"] = max(0, int(previous.get("page", 0)))
    if trigger == f"{prefix}-expand":
        state.update(expanded=not state["expanded"], page=0)
    elif state["expanded"] and trigger == f"{prefix}-next" and previous.get("has_next"):
        state["page"] += 1
    elif state["expanded"] and trigger == f"{prefix}-previous":
        state["page"] = max(0, state["page"] - 1)
    return state


def ranking_page(loader, previous, selection, trigger, prefix, valid, school=False):
    """Top 10 or a bounded 50-row page; never accumulate rows in browser stores.

    Fetch one additional row to detect a next page without a separate COUNT.
    The store contains only paging metadata, not student or school records.
    """
    state = next_paging_state(previous, selection, trigger, prefix)
    size = 50 if state["expanded"] else 10
    offset = state["page"] * size
    unit = "students" if school else "schools"
    label = "Show top 10 only" if state["expanded"] else f"Show all {unit}"
    hidden = {"display": "none"}
    if not valid:
        return empty_state(), label, hidden, hidden, True, True, "", state
    try:
        df = loader(size + 1, offset)
        # Data can change between page clicks. A deleted last page returns to 1.
        if df.empty and offset:
            state["page"], offset = 0, 0
            df = loader(size + 1, 0)
        state["has_next"] = len(df) > size
        visible = df.head(size)
        table = build_detail_ranking(visible, school=school)
    except Exception as exc:
        if not isinstance(exc, QueryError):
            logger.exception("Analytics ranking failed")
        return empty_state(ERROR_MESSAGE), label, hidden, hidden, True, True, "", state
    toggle_style = {} if state["expanded"] or state["has_next"] else hidden
    pager_style = {} if state["expanded"] and not visible.empty else hidden
    status = f"Page {state['page'] + 1} · {offset + 1}–{offset + len(visible)} · up to 50 per page"
    return (table, label, toggle_style, pager_style, state["page"] == 0,
            not state["has_next"], status, state)
