"""
Reader for a filing's rendered reports.

Every XBRL filing ships with ``FilingSummary.xml`` (the list of rendered
reports, with roles and long names) and one ``R<n>.htm`` file per report
(the rendered statement table). This module handles fetching and
caching; the actual HTML parsing lives in :mod:`.report_html` and needs
no third-party dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .report_html import (  # noqa: F401 - re-exported for backward compatibility
    normalize_period_label,
    parse_report_html,
    parse_report_number,
)

logger = logging.getLogger(__name__)


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
        return parse_report_html(raw)
