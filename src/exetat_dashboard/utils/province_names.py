"""
province_names.py
==================

Single source of truth for turning a province name — coming from either
the database or the GeoJSON — into a canonical key that can be compared
safely.

Why this exists
----------------
`figures/map.py`'s Plotly Choropleth joins `df[location_col]` to
`geojson["features"][i]["properties"][...]` on an EXACT string match
(via `featureidkey`). Both sides are supposed to already use the same
"reconciled" convention (uppercase French, hyphenated, e.g.
"HAUT-UELE"), but relying on two independently-maintained data sources
(a hand-edited GeoJSON property and a database column) to always agree
byte-for-byte is fragile — a single accent, extra space, "-" vs " ",
or a differently-cased row is enough to break that one province's
match while everything else keeps working, which is exactly the
"only NORD-UBANGI renders" symptom this module was added to fix.

Rather than hand-patching individual mismatched names (which the
project brief explicitly asked us not to do), every consumer should
route both sides of the join through `normalize_province_name()` so
the match is robust to case, accents, and hyphen/space punctuation —
regardless of which side (DB or GeoJSON) happens to be "correct".
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

__all__ = ["normalize_province_name"]


def normalize_province_name(value: Optional[str]) -> Optional[str]:
    """
    Canonicalize a province name for matching purposes.

    - Strips leading/trailing whitespace.
    - Strips accents (e.g. "É" -> "E").
    - Uppercases.
    - Collapses hyphens/underscores/repeated whitespace into a single
      space, so "Haut-Uele", "HAUT UELE", "haut_uele" and "HAUT-UELE"
      all normalize to the same key: "HAUT UELE".

    None / empty input returns None (so it never accidentally matches
    another None).
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Strip accents: decompose then drop combining marks.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    text = text.upper()

    # Treat hyphens/underscores the same as spaces, then collapse.
    text = re.sub(r"[-_]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None
