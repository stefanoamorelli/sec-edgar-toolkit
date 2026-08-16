"""
Typed document metadata from a filing's index page.

The archive folder listing (index.json) only carries file names and
sizes. The filing index page lists every document with its sequence,
description, and SEC document type (10-K, EX-99.1, GRAPHIC, ...), which
is what identifies exhibits reliably.
"""

from __future__ import annotations

import re
from typing import Dict, List

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _document_name(cell_html: str) -> str:
    match = re.search(r'href="([^"]+)"', cell_html)
    if match:
        href = match.group(1)
        # iXBRL viewer links wrap the real document path
        href = href.split("/ix?doc=")[-1]
        return href.rsplit("/", 1)[-1]
    return _strip_tags(cell_html)


def parse_filing_index_html(html: "str | bytes") -> List[Dict[str, str]]:
    """
    Parse a filing index page into typed document records.

    Returns:
        One record per listed document:
        ``{"sequence", "description", "document", "type", "size"}``
    """
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="ignore")

    records: List[Dict[str, str]] = []
    for row_match in _ROW_RE.finditer(html):
        cells = _CELL_RE.findall(row_match.group(1))
        if len(cells) < 5:
            continue
        document = _document_name(cells[2])
        if not document:
            continue
        records.append(
            {
                "sequence": _strip_tags(cells[0]),
                "description": _strip_tags(cells[1]),
                "document": document,
                "type": _strip_tags(cells[3]),
                "size": _strip_tags(cells[4]),
            }
        )
    return records
