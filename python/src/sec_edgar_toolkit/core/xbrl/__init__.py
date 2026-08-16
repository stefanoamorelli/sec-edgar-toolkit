"""XBRL access for one filing: fact queries and rendered-report statements."""

from .instance import XBRLInstance
from .queries import FactQuery, FactsData
from .rendered_reports import RenderedReportReader
from .report_html import (
    normalize_period_label,
    parse_report_html,
    parse_report_number,
)
from .statements import STATEMENT_CONCEPTS, normalize_statement_type

__all__ = [
    "XBRLInstance",
    "FactQuery",
    "FactsData",
    "RenderedReportReader",
    "parse_report_html",
    "parse_report_number",
    "normalize_period_label",
    "STATEMENT_CONCEPTS",
    "normalize_statement_type",
]
