import os
import pdfplumber
import json
import re
import gc
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter


# Year patterns
YEAR_DELIMITER = re.compile(r'[-\s](20\d{2})[-\s]')   # year between dashes/spaces
_RE_YEAR_BARE  = re.compile(r'20\d{2}')               # any 4-digit year starting with 20

# Header keyword patterns
_RE_OPTION = re.compile(
    r'[Oo][Pp][Tt][Ii][Oo][Nn]\s*:\s*'           # OPTION / Option / option
    r'(.+?)'                                       # captured value (non-greedy)
    r'(?:'
        r'\s*-?\s*[Pp][Rr][Oo][Vv][Ii][Nn][Cc][Ee]\s*:'   # stop at PROVINCE:
        r'|\s*-?\s*[Cc][Oo][Dd][Ee]\s*:'                   # stop at CODE:
        r'|$'
    r')',
    re.DOTALL
)

_RE_PROVINCE = re.compile(
    r'[Pp][Rr][Oo][Vv][Ii][Nn][Cc][Ee]\s*:\s*'
    r'(.+?)'
    r'(?:\s*-?\s*[Cc][Oo][Dd][Ee]\s*:|$)',
    re.DOTALL
)

_RE_OPTION_SECTION = re.compile(           # fallback: get text after OPTION: up to CODE:
    r'[Oo][Pp][Tt][Ii][Oo][Nn]\s*:\s*(.+?)(?:\s*-?\s*[Cc][Oo][Dd][Ee]\s*:|$)',
    re.DOTALL
)

# Body-line label prefixes
_RE_LABEL_CODE         = re.compile(r'^[Cc]ode\s*:\s*')
_RE_LABEL_PARTICIPANTS = re.compile(r'^[Pp]articipants?\s*:\s*')
_RE_LABEL_REUSSITES    = re.compile(r'^R[ée][uú]ssites?\s*:\s*', re.IGNORECASE)

# "Dont: X F" suffix that appears in participant / réussites cells
_RE_DONT_SUFFIX = re.compile(r'\s*[Dd]ont\s*:.*$', re.DOTALL)

# Trigger sentinel: a line that begins a réussites entry
_RE_REUSSITES_LINE = re.compile(r'^R[ée][uú]ssites?\s*:', re.IGNORECASE)

# Student-line sentinel: require rank, name, and gender/score field
_RE_STUDENT_START = re.compile(
    r'^\d+\s+'                  # rank
    r'.+?\s+'                    # name
    r'(?:[MFmf]\s*\d+|[MFmf]\d+)'  # gender + score (M 72, M72, F 88, F88)
    r'\s*$'
)

# Full student line parser — two formats in one pattern:
#   Format A: <rank>  <name…>  <M|F>  <score>     separate gender + score
#   Format B: <rank>  <name…>  <M|F><score>        combined, e.g. "M72"
_RE_STUDENT = re.compile(
    r'^(?P<rank>\d+)\s+'
    r'(?P<name>.+?)\s+'
    r'(?:'
        r'(?P<gender_sep>[MFmf])\s+(?P<score_sep>\d+)'
        r'|'
        r'(?P<gender_score>[MFmf]\d+)'
    r')$'
)

# Normalise réussites: keep only digits and dots
_RE_REUSSITE_NOISE = re.compile(r'[^\d.]+')

# Néant / Zéro / empty → treat as 0
_RE_NEANT = re.compile(
    r'^\s*(?:N[ée]ant|Z[ée]ro|0)(?:\s*[-–—].*)?$',
    re.IGNORECASE
)

# Null-byte cleaner
_RE_NULL = re.compile(r'\x00')

def _strip_null(text: str) -> str:
    """Remove null bytes from the given text string."""
    return _RE_NULL.sub('', text) if text else ''


def _clean_dont(value: str) -> str:
    """Remove trailing 'Dont: X F' fragment."""
    return _RE_DONT_SUFFIX.sub('', value).strip()


def normalize_reussite_value(value: str) -> str:
    """Return '0' for Néant/Zéro/empty, otherwise strip non-numeric chars."""
    if not value or _RE_NEANT.match(value):
        return "0"
    return _RE_REUSSITE_NOISE.sub('', value.strip()) or value.strip()


# Year helpers

def find_year(text: str) -> str:
    """Find a 4-digit year (20xx) in *text*."""
    m = YEAR_DELIMITER.search(text)
    if m:
        return m.group(1)
    m = _RE_YEAR_BARE.search(text)
    return m.group(0) if m else ""


def extract_year(footer_text: str, filename: str = "") -> str:
    """Return year from footer, falling back to filename."""
    if not footer_text and not filename:
        return ""
    if footer_text:
        year = find_year(footer_text)
        if year:
            return year
    return find_year(filename) if filename else ""

# Header field extractors
def extract_option(header_text: str) -> str:
    """Extract the option field from the page header."""
    if not header_text:
        return ""
    m = _RE_OPTION.search(header_text)
    if m:
        return m.group(1).strip()
    return ""



def extract_province(header_text: str) -> str:
    """Extract province from header, with OPTION-line fallback."""
    if not header_text:
        return ""

    # 1. Explicit PROVINCE keyword
    m = _RE_PROVINCE.search(header_text)
    if m:
        return m.group(1).strip()

    # 2. Fallback: last "/" segment of the OPTION line
    m = _RE_OPTION_SECTION.search(header_text)
    if m:
        option_section = m.group(1)
        if '/' in option_section:
            parts = option_section.split('/')
            province = ' '.join(parts[-1].split()).strip()
            if province and not province.isdigit():
                return province

    return ""

# Body data extractors
def school_data(sections: dict, filename: str = "") -> dict:
    """Extract per-school summary rows (participants / réussites)."""
    result = {"school_option": "", "school_province": "", "schools": []}

    footer_text   = sections.get("footer", "")
    year          = extract_year(footer_text, filename)
    header_text   = sections.get("header", "")
    page_option   = extract_option(header_text)
    page_province = extract_province(header_text)

    result["school_option"]   = page_option
    result["school_province"] = page_province

    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result

    lines = [ln.strip() for ln in body_text.split('\n') if ln.strip()]

    for i, line in enumerate(lines):
        if not _RE_REUSSITES_LINE.match(line) or i < 3:
            continue

        code_clean         = _RE_LABEL_CODE.sub('', lines[i - 2]).strip()
        participants_clean = _clean_dont(_RE_LABEL_PARTICIPANTS.sub('', lines[i - 1]).strip())
        reussites_clean    = normalize_reussite_value(
                                _clean_dont(_RE_LABEL_REUSSITES.sub('', line).strip())
                             )

        result["schools"].append({
            "school_name":         lines[i - 3].strip(),
            "school_code":         code_clean,
            "school_participants": participants_clean,
            "school_reussites":    reussites_clean,
            "school_option":       page_option,
            "school_province":     page_province,
            "year":                year,
        })

    return result


def student_data(sections: dict, filename: str = "") -> dict:
    """Extract per-student records grouped by school."""
    result = {"students_by_school": []}

    footer_text   = sections.get("footer", "")
    year          = extract_year(footer_text, filename)
    header_text   = sections.get("header", "")
    page_option   = extract_option(header_text)
    page_province = extract_province(header_text)

    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result

    lines = [ln.strip() for ln in body_text.split('\n') if ln.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        if _RE_REUSSITES_LINE.match(line) and i >= 3:
            school_code = _RE_LABEL_CODE.sub('', lines[i - 2]).strip()
            school_students = {
                "school_name": lines[i - 3].strip(),
                "school_code": school_code,
                "option":      page_option,
                "province":    page_province,
                "year":        year,
                "students":    [],
            }

            j = i + 1
            while j < len(lines):
                student_line = lines[j].strip()
                if _RE_STUDENT_START.match(student_line):
                    info = parse_student_line(student_line, school_code)
                    if info:
                        school_students["students"].append(info)
                    j += 1
                else:
                    break

            if school_students["students"]:
                result["students_by_school"].append(school_students)

        i += 1

    return result


def parse_student_line(line: str, school_code: str) -> dict | None:
    """
    Parse one student line.

    Format A → <rank> <name…> <M|F> <score>   (gender and score are separate tokens)
    Format B → <rank> <name…> <M|F><score>     (combined, e.g. "M72")
    """
    m = _RE_STUDENT.match(line.strip())
    if not m:
        return None

    rank = m.group('rank')
    name = m.group('name').strip()

    if m.group('gender_score'):          # Format B
        gs     = m.group('gender_score')
        gender = gs[0].upper()
        score  = gs[1:]
    else:                                # Format A
        gender = (m.group('gender_sep') or '').upper()
        score  = m.group('score_sep') or ''

    return {
        "name":         name,
        "student_code": f"{school_code}/ {rank}",
        "sexe":         gender,
        "pourcentage":  score,
    }


