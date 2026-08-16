"""
Reader for a filing's rendered reports.

Every XBRL filing ships with ``FilingSummary.xml`` (the list of rendered
reports, with roles and long names) and one ``R<n>.htm`` file per report
(the rendered statement table). Parsing those gives filing-scoped
statement structure — roles, line-item concepts, per-period values, and
dimensional detail such as segment breakdowns — without a full XBRL
processor.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

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


class RenderedReportReader:
    """
    Lists and parses a filing's rendered reports.

    Only depends on an HTTP client (``get_raw(url) -> bytes``) and the
    filing's archive-folder base URL, so it is reusable outside
    ``XBRLInstance``.
    """

    def __init__(self, archive_base: str, http_client: Any) -> None:
        self._archive_base = archive_base
        self._http = http_client
        self._reports: Optional[List[Dict[str, Any]]] = None
        self._statement_cache: Dict[str, List[Dict[str, Any]]] = {}

    def list_reports(self) -> List[Dict[str, Any]]:
        """Parse FilingSummary.xml into a list of report descriptors."""
        if self._reports is not None:
            return self._reports

        import xml.etree.ElementTree as ET

        url = f"{self._archive_base}/FilingSummary.xml"
        try:
            raw = self._http.get_raw(url)
        except Exception as e:
            logger.warning(f"No FilingSummary.xml at {url}: {e}")
            self._reports = []
            return self._reports

        reports: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(raw)
            for report in root.iter("Report"):
                descriptor = {
                    "definition": (report.findtext("LongName") or "").strip(),
                    "short_name": (report.findtext("ShortName") or "").strip(),
                    "role": (report.findtext("Role") or "").strip(),
                    "r_file": (report.findtext("HtmlFileName") or "").strip(),
                    "report_type": (report.findtext("ReportType") or "").strip(),
                }
                if descriptor["role"] or descriptor["r_file"]:
                    reports.append(descriptor)
        except ET.ParseError as e:
            logger.warning(f"Could not parse FilingSummary.xml: {e}")

        self._reports = reports
        return reports

    def find_report(self, role: str) -> Optional[Dict[str, Any]]:
        """Find a report by role URI, R-file name, or short name."""
        for report in self.list_reports():
            if role in (report["role"], report["r_file"], report["short_name"]):
                return report
        # Loose match on the role suffix
        role_lower = role.lower()
        for report in self.list_reports():
            if report["role"].lower().endswith(role_lower):
                return report
        return None

    def read_statement(self, role: str) -> List[Dict[str, Any]]:
        """
        Parse one rendered report into line items.

        Args:
            role: The report's role URI (from ``list_reports()``), its
                R-file name, or its short name.

        Returns:
            List of line-item dicts with ``concept``, ``label``,
            ``section``, ``values`` (period -> number), ``units``
            (period -> unit), and ``has_values`` keys.
        """
        report = self.find_report(role)
        if not report or not report.get("r_file"):
            return []

        cache_key = report["r_file"]
        if cache_key in self._statement_cache:
            return self._statement_cache[cache_key]

        url = f"{self._archive_base}/{report['r_file']}"
        try:
            raw = self._http.get_raw(url)
        except Exception as e:
            logger.warning(f"Could not fetch report {url}: {e}")
            return []

        items = self._parse_report_html(raw)
        self._statement_cache[cache_key] = items
        return items

    def _parse_report_html(self, raw: bytes) -> List[Dict[str, Any]]:
        """Parse an R<n>.htm rendered report table into line items."""
        try:
            from lxml import html as lxml_html
        except ImportError:
            logger.warning("lxml is required to parse rendered reports")
            return []

        try:
            tree = lxml_html.fromstring(raw)
        except Exception as e:
            logger.warning(f"Could not parse report HTML: {e}")
            return []

        tables = tree.xpath("//table[contains(@class, 'report')]") or tree.xpath(
            "//table"
        )
        if not tables:
            return []
        table = tables[0]

        multiplier, shares_multiplier = self._parse_multipliers(table)
        periods = self._parse_period_headers(table)

        items: List[Dict[str, Any]] = []
        # Dimensional reports group measure rows under axis-member rows
        # ("Americas | Operating segments"); carry that grouping onto the
        # measure rows so labels stay meaningful on their own.
        current_section = ""
        for row in table.xpath(".//tr"):
            label_cells = row.xpath("./td[contains(@class, 'pl')]")
            if not label_cells:
                continue
            label_cell = label_cells[0]
            label = " ".join(label_cell.itertext()).strip()
            label = re.sub(r"\s+", " ", label)

            concept = ""
            onclick_nodes = label_cell.xpath(".//a/@onclick")
            if onclick_nodes:
                match = re.search(r"defref_([A-Za-z0-9_-]+)", onclick_nodes[0])
                if match:
                    concept = match.group(1).replace("_", ":", 1)

            values, units = self._parse_value_cells(
                row, label, concept, periods, multiplier, shares_multiplier
            )

            if not values and concept.endswith("Axis"):
                current_section = label

            section = current_section if values else ""
            items.append(
                {
                    "concept": concept,
                    "label": f"{section} | {label}" if section else label,
                    "base_label": label,
                    "section": section,
                    "values": values,
                    "units": units,
                    "has_values": bool(values),
                }
            )

        return items

    def _parse_multipliers(self, table) -> tuple:
        """Unit multipliers from the report title cell (e.g. "$ in Millions")."""
        multiplier = 1.0
        header_text = " ".join(table.xpath(".//th//text()"))
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

    def _parse_period_headers(self, table) -> List[str]:
        """Period labels from the last header row (skipping the label column)."""
        header_rows = [row for row in table.xpath(".//tr") if row.xpath("./th")]
        if not header_rows:
            return []
        cells = header_rows[-1].xpath("./th")
        texts = [" ".join(c.itertext()).strip() for c in cells]
        # Drop the leading label-column header when present
        if texts and not re.search(r"\d{4}", texts[0]):
            texts = texts[1:]
        return [normalize_period_label(t) for t in texts if t]

    def _parse_value_cells(
        self,
        row,
        label: str,
        concept: str,
        periods: List[str],
        multiplier: float,
        shares_multiplier: float,
    ) -> tuple:
        """Numeric values and units for one report row, keyed by period."""
        values: Dict[str, float] = {}
        units: Dict[str, str] = {}
        value_cells = row.xpath(
            "./td[contains(@class, 'nump') or contains(@class, 'num')"
            " or contains(@class, 'text')]"
        )
        column = 0
        for cell in value_cells:
            cell_class = cell.get("class", "")
            if "num" not in cell_class:
                column += 1
                continue
            text = " ".join(cell.itertext()).strip()
            # Strip footnote markers like [1]
            text = re.sub(r"\[\d+\]", "", text).strip()
            number = parse_report_number(text)
            if number is not None:
                period = periods[column] if column < len(periods) else f"col_{column}"
                is_shares = "shares" in label.lower() or (
                    concept and "shares" in concept.lower()
                )
                is_per_share = "per share" in label.lower() or (
                    concept and "pershare" in concept.lower().replace("-", "")
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
        return values, units
