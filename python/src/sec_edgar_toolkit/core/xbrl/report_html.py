"""
Pure parser for rendered report files (``R<n>.htm``).

The files are machine-generated and highly regular, so a regex-based
parser is reliable here and keeps the dependency footprint at zero
(the same implementation the TypeScript package uses). No I/O happens
in this module.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_NUMBER_RE = re.compile(r"^[\s$]*\(?\s*-?[\d,]+(?:\.\d+)?\s*\)?[\s%]*$")

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_PERIOD_DATE_RE = re.compile(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\s*$")

_TABLE_REPORT_RE = re.compile(
    r"<table[^>]*class=\"report\"[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL
)
_TABLE_ANY_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.IGNORECASE | re.DOTALL)
_TD_RE = re.compile(r"<td([^>]*)>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_CLASS_RE = re.compile(r"class=\"([^\"]*)\"", re.IGNORECASE)
_DEFREF_RE = re.compile(r"defref_([A-Za-z0-9_-]+)")


def normalize_period_label(label: str) -> str:
    """Normalize a report period header ("Sep. 27, 2025") to ISO (2025-09-27)."""
    match = _PERIOD_DATE_RE.search(label)
    if not match:
        return label
    month = _MONTHS.get(match.group(1).lower()[:3])
    if not month:
        return label
    return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}"


def parse_report_number(text: str) -> Optional[float]:
    """Parse a rendered report cell like ``$ (1,234.5)`` into a float."""
    if not text:
        return None
    cleaned = text.strip()
    if not _NUMBER_RE.match(cleaned):
        return None
    negative = "(" in cleaned
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = text.replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _parse_multipliers(header_text: str) -> Tuple[float, float]:
    multiplier = 1.0
    if re.search(r"in\s+Millions", header_text, re.IGNORECASE):
        multiplier = 1e6
    elif re.search(r"in\s+Thousands", header_text, re.IGNORECASE):
        multiplier = 1e3
    elif re.search(r"in\s+Billions", header_text, re.IGNORECASE):
        multiplier = 1e9
    shares_multiplier = multiplier
    if re.search(r"shares\s+in\s+Millions", header_text, re.IGNORECASE):
        shares_multiplier = 1e6
    elif re.search(r"shares\s+in\s+Thousands", header_text, re.IGNORECASE):
        shares_multiplier = 1e3
    return multiplier, shares_multiplier


def _parse_period_headers(rows: List[str]) -> List[str]:
    header_rows = [row for row in rows if _TH_RE.search(row)]
    if not header_rows:
        return []
    texts = [_strip_tags(cell) for cell in _TH_RE.findall(header_rows[-1])]
    # Drop the leading label-column header when present
    if texts and not re.search(r"\d{4}", texts[0]):
        texts = texts[1:]
    return [normalize_period_label(t) for t in texts if t]


def _cell_class(attrs: str) -> str:
    match = _CLASS_RE.search(attrs)
    return match.group(1) if match else ""


def parse_report_html(raw: bytes | str) -> List[Dict[str, Any]]:
    """Parse an R<n>.htm rendered report table into line items."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")

    table_match = _TABLE_REPORT_RE.search(raw) or _TABLE_ANY_RE.search(raw)
    if not table_match:
        return []
    table = table_match.group(1)

    rows = _ROW_RE.findall(table)

    header_text = " ".join(
        _strip_tags(cell) for row in rows for cell in _TH_RE.findall(row)
    )
    multiplier, shares_multiplier = _parse_multipliers(header_text)
    periods = _parse_period_headers(rows)

    items: List[Dict[str, Any]] = []
    # Dimensional reports group measure rows under axis-member rows
    # ("Americas | Operating segments"); carry that grouping onto the
    # measure rows so labels stay meaningful on their own.
    current_section = ""
    for row in rows:
        cells = _TD_RE.findall(row)
        if not cells:
            continue
        label_cell = next(
            (cell for cell in cells if "pl" in _cell_class(cell[0])), None
        )
        if label_cell is None:
            continue

        label = _strip_tags(label_cell[1])

        concept = ""
        defref = _DEFREF_RE.search(label_cell[1])
        if defref:
            concept = defref.group(1).replace("_", ":", 1)

        values: Dict[str, float] = {}
        units: Dict[str, str] = {}
        column = 0
        for attrs, content in cells:
            cell_class = _cell_class(attrs)
            is_numeric = "num" in cell_class
            if not is_numeric:
                if "text" in cell_class:
                    column += 1
                continue
            text = re.sub(r"\[\d+\]", "", _strip_tags(content)).strip()
            number = parse_report_number(text)
            if number is not None:
                period = periods[column] if column < len(periods) else f"col_{column}"
                is_shares = "shares" in label.lower() or "shares" in concept.lower()
                is_per_share = (
                    "per share" in label.lower()
                    or "pershare" in concept.lower().replace("-", "")
                )
                if is_per_share:
                    scale = 1.0
                elif is_shares:
                    scale = shares_multiplier
                else:
                    scale = multiplier
                values[period] = number * scale
                units[period] = (
                    "shares" if is_shares else "USD/shares" if is_per_share else "USD"
                )
            column += 1

        has_values = bool(values)
        if not has_values and concept.endswith("Axis"):
            current_section = label

        section = current_section if has_values else ""
        items.append(
            {
                "concept": concept,
                "label": f"{section} | {label}" if section else label,
                "base_label": label,
                "section": section,
                "values": values,
                "units": units,
                "has_values": has_values,
            }
        )

    return items
