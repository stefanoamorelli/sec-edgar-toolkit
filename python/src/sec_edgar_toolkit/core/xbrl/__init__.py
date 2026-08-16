"""XBRL access for one filing: fact queries and rendered-report statements."""

from .instance import XBRLInstance
from .queries import FactQuery, FactsData
from .rendered_reports import RenderedReportReader
from .statements import STATEMENT_CONCEPTS, normalize_statement_type

__all__ = [
    "XBRLInstance",
    "FactQuery",
    "FactsData",
    "RenderedReportReader",
    "STATEMENT_CONCEPTS",
    "normalize_statement_type",
]
