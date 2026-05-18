import os
import re
import pdfplumber


# PDF layout helpers

_RE_NULL = re.compile(r'\x00')

def _strip_null(text: str) -> str:
    """Remove null bytes from the given text string."""
    return _RE_NULL.sub('', text) if text else ''


def extract_header(page, path: str, header_adjustement: float = 0.05) -> dict:
    """Extract text from the page header and footer bands."""
    width, height = page.width, page.height

    if path.endswith("style_2"):
        header_adjustement = 0.09

    footer_start = 1.0 - header_adjustement

    header = page.within_bbox((0, 0, width, height * header_adjustement)).extract_text(layout=True)
    footer = page.within_bbox((0, height * footer_start, width, height)).extract_text(layout=True)

    return {
        "header": _strip_null(header or ""),
        "footer": _strip_null(footer or ""),
    }


def extract_body(page, path: str, header_adjustement: float = 0.05) -> str:
    """Extract three-column body text, preserving layout."""
    width, height = page.width, page.height

    if path.endswith("style_2"):
        header_adjustement = 0.09

    body_top    = height * header_adjustement
    body_bottom = height * (1.0 - header_adjustement)
    col         = width / 3

    # Column bounding-box multipliers per document style
    if path.endswith("style_2"):
        bboxes = [
            (0,            body_top, col * 1.08,  body_bottom),
            (col * 1.05,   body_top, col * 1.94,  body_bottom),
            (col * 1.90,   body_top, width,        body_bottom),
        ]
    elif path.endswith("pdf_2008"):
        bboxes = [
            (0,            body_top, col * 1.15,  body_bottom),
            (col * 1.15,   body_top, col * 2.03,  body_bottom),
            (col * 2.05,   body_top, width,        body_bottom),
        ]
    else:
        bboxes = [
            (0,            body_top, col * 1.1,   body_bottom),
            (col * 1.1,    body_top, col * 2.0,   body_bottom),
            (col * 1.93,   body_top, width,        body_bottom),
        ]

    body = "".join(
        page.within_bbox(bbox).extract_text(layout=True) or ""
        for bbox in bboxes
    )
    return _strip_null(body)
