import os
import pdfplumber
import json
import re
import gc
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from pdf_helper import extract_header, extract_body
# ── Regex patterns ────────────────────────────────────────────────────────────

YEAR_DELIMITER = re.compile(r'[-\s](20\d{2})[-\s]')
_RE_YEAR_BARE  = re.compile(r'20\d{2}')

_RE_OPTION = re.compile(
    r'[Oo][Pp][Tt][Ii][Oo][Nn]\s*:\s*'
    r'(.+?)'
    r'(?:\s*-?\s*[Pp][Rr][Oo][Vv][Ii][Nn][Cc][Ee]\s*:'
    r'|\s*-?\s*[Cc][Oo][Dd][Ee]\s*:'
    r'|$)',
    re.DOTALL,
)
_RE_PROVINCE = re.compile(
    r'[Pp][Rr][Oo][Vv][Ii][Nn][Cc][Ee]\s*:\s*'
    r'(.+?)'
    r'(?:\s*-?\s*[Cc][Oo][Dd][Ee]\s*:|$)',
    re.DOTALL,
)
_RE_OPTION_SECTION = re.compile(
    r'[Oo][Pp][Tt][Ii][Oo][Nn]\s*:\s*(.+?)(?:\s*-?\s*[Cc][Oo][Dd][Ee]\s*:|$)',
    re.DOTALL,
)

_RE_LABEL_CODE         = re.compile(r'^[Cc]ode\s*:\s*')
_RE_LABEL_PARTICIPANTS = re.compile(r'^[Pp]articipants?\s*:\s*')
_RE_LABEL_REUSSITES    = re.compile(r'^R[ée][uú]ssites?\s*:\s*', re.IGNORECASE)
_RE_DONT_SUFFIX        = re.compile(r'\s*[Dd]ont\s*:.*$', re.DOTALL)
_RE_REUSSITES_LINE     = re.compile(r'^R[ée][uú]ssites?\s*:',    re.IGNORECASE)
_RE_REUSSITE_NOISE     = re.compile(r'[^\d.]+')
_RE_NEANT              = re.compile(
    r'^\s*(?:N[ée]ant|Z[ée]ro|0)(?:\s*[-–—].*)?$', re.IGNORECASE
)

# FIX 1 — added |\d+  so no-gender autodidacte lines are recognised
_RE_STUDENT_START = re.compile(
    r'^\d+\s+'
    r'.+?\s+'
    r'(?:[MFmf]\s*\d+|[MFmf]\d+|\d+)'   # gender+score  OR  score-only
    r'\s*$'
)

# FIX 1 — added score_only group for autodidactes (no gender recorded)
_RE_STUDENT = re.compile(
    r'^(?P<rank>\d+)\s+'
    r'(?P<name>.+?)\s+'
    r'(?:'
        r'(?P<gender_sep>[MFmf])\s+(?P<score_sep>\d+)'   # "M 72"
        r'|'
        r'(?P<gender_score>[MFmf]\d+)'                   # "M72"
        r'|'
        r'(?P<score_only>\d+)'                           # "72"  (no gender)
    r')$'
)


# ── Small utilities ───────────────────────────────────────────────────────────

def _clean_dont(value: str) -> str:
    return _RE_DONT_SUFFIX.sub('', value).strip()


def normalize_reussite_value(value: str) -> str:
    if not value or _RE_NEANT.match(value):
        return "0"
    return _RE_REUSSITE_NOISE.sub('', value.strip()) or value.strip()


def find_year(text: str) -> str:
    m = YEAR_DELIMITER.search(text)
    if m:
        return m.group(1)
    m = _RE_YEAR_BARE.search(text)
    return m.group(0) if m else ""


def extract_year(footer_text: str, filename: str = "") -> str:
    if footer_text:
        year = find_year(footer_text)
        if year:
            return year
    return find_year(filename) if filename else ""


def extract_option(header_text: str) -> str:
    if not header_text:
        return ""
    m = _RE_OPTION.search(header_text)
    return m.group(1).strip() if m else ""


def extract_province(header_text: str) -> str:
    if not header_text:
        return ""
    m = _RE_PROVINCE.search(header_text)
    if m:
        return m.group(1).strip()
    m = _RE_OPTION_SECTION.search(header_text)
    if m:
        option_section = m.group(1)
        if '/' in option_section:
            parts    = option_section.split('/')
            province = ' '.join(parts[-1].split()).strip()
            if province and not province.isdigit():
                return province
    return ""


def parse_student_line(line: str, school_code: str) -> dict | None:
    """
    Parse one student line.
      Format A → <rank> <name…> <M|F> <score>      gender and score separate
      Format B → <rank> <name…> <M|F><score>        combined, e.g. "M72"
      Format C → <rank> <name…> <score>             no gender (autodidactes)
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
    elif m.group('gender_sep'):          # Format A
        gender = m.group('gender_sep').upper()
        score  = m.group('score_sep') or ''
    else:                                # Format C — no gender recorded
        gender = ''
        score  = m.group('score_only') or ''

    return {
        "name":         name,
        "student_code": f"{school_code}/ {rank}",
        "sexe":         gender,
        "pourcentage":  score,
    }


# ── FIX 2: page-section builder ───────────────────────────────────────────────

def build_page_sections(pdf, path: str = "") -> list[list[tuple]]:
    """
    Group all pages into sections where every page in a section shares the
    same Option header value. Each section is a flat list of tuples:

        (line_text, option, province, year)

    Because consecutive pages with the same Option are merged into one list,
    a school block that starts on page N and overflows to page N+1 is seen as
    a single contiguous sequence — no orphaned student lines at the top of a
    continuation page.

    When the Option header changes, a new section begins automatically, so
    schools from different options never bleed into each other.
    """
    sections    = []
    cur_option  = None
    cur_province = None
    cur_year    = None
    cur_lines   = []

    for page in pdf.pages:
        hf       = extract_header(page, path)
        body     = extract_body(page, path)
        h_text   = hf['header']
        f_text   = hf['footer']

        option   = extract_option(h_text)
        province = extract_province(h_text)
        year     = extract_year(f_text)

        # Propagate missing values on continuation pages.
        if not option and cur_option is not None:
            option = cur_option
        if not province and cur_province is not None:
            province = cur_province
        if not year and cur_year is not None:
            year = cur_year

        # Option boundary → save finished section, open a new one.
        if option != cur_option:
            if cur_lines:
                sections.append(cur_lines)
            cur_lines   = []
            cur_option  = option
            cur_province = province
            cur_year    = year

        for raw in body.split('\n'):
            stripped = raw.strip()
            if stripped:
                cur_lines.append((stripped, option, province, year))

    if cur_lines:                        # flush the last section
        sections.append(cur_lines)

    return sections


# ── Main extractors ───────────────────────────────────────────────────────────

def school_data(pdf, path: str = "", filename: str = "") -> list[dict]:
    """
    Extract per-school summary rows (participants / réussites).
    Returns a flat list of school dicts.
    """
    result   = []
    sections = build_page_sections(pdf, path)

    for section_lines in sections:
        i = 0
        while i < len(section_lines):
            text, option, province, year = section_lines[i]

            if _RE_REUSSITES_LINE.match(text) and i >= 3:
                school_name  = section_lines[i - 3][0]
                code_raw     = section_lines[i - 2][0]
                part_raw     = section_lines[i - 1][0]

                school_code  = _RE_LABEL_CODE.sub('', code_raw).strip()
                participants = _clean_dont(
                    _RE_LABEL_PARTICIPANTS.sub('', part_raw).strip()
                )
                reussites    = normalize_reussite_value(
                    _clean_dont(_RE_LABEL_REUSSITES.sub('', text).strip())
                )

                result.append({
                    "school_name":         school_name,
                    "school_code":         school_code,
                    "school_participants": participants,
                    "school_reussites":    reussites,
                    "school_option":       option,
                    "school_province":     province,
                    "year":                year,
                })

            i += 1

    return result


def student_data(pdf, path: str = "", filename: str = "") -> list[dict]:
    """
    Extract per-student records grouped by school.
    Returns a list of school dicts each containing a 'students' list.

    Schools with zero réussites are included but have an empty students list.
    """
    result   = []
    sections = build_page_sections(pdf, path)

    for section_lines in sections:
        i = 0
        while i < len(section_lines):
            text, option, province, year = section_lines[i]

            if _RE_REUSSITES_LINE.match(text) and i >= 3:
                school_name = section_lines[i - 3][0]
                code_raw    = section_lines[i - 2][0]
                school_code = _RE_LABEL_CODE.sub('', code_raw).strip()

                school_rec = {
                    "school_name": school_name,
                    "school_code": school_code,
                    "option":      option,
                    "province":    province,
                    "year":        year,
                    "students":    [],
                    #TODO : make this a set in order to avoid duplication entry 
                }

                # Consume all following student lines
                j = i + 1
                while j < len(section_lines):
                    s_text = section_lines[j][0]
                    if _RE_STUDENT_START.match(s_text):
                        info = parse_student_line(s_text, school_code)
                        if info:
                            school_rec["students"].append(info)
                        j += 1
                    else:
                        break

                result.append(school_rec)
                i = j          # skip past the student block we just consumed
                continue

            i += 1

    return result
