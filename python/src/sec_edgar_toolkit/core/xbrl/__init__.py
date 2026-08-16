"""XBRL access for one filing: fact queries and rendered-report statements."""

from .as_reported import AsReportedStatements
from .instance import XBRLInstance
from .instance_document import Context, InstanceDocument, InstanceFact
from .linkbases import LabelLinkbase, PresentationLinkbase, PresentationNode
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
    "AsReportedStatements",
    "InstanceDocument",
    "InstanceFact",
    "Context",
    "PresentationLinkbase",
    "PresentationNode",
    "LabelLinkbase",
    "FactQuery",
    "FactsData",
    "RenderedReportReader",
    "parse_report_html",
    "parse_report_number",
    "normalize_period_label",
    "STATEMENT_CONCEPTS",
    "normalize_statement_type",
]
