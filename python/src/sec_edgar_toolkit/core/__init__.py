"""Core classes and functions providing edgartools-compatible API."""

from .company import Company
from .filing import Filing
from .global_functions import find_company, get_filings, search, set_identity
from .xbrl import XBRLInstance

__all__ = [
    "Company",
    "Filing",
    "XBRLInstance",
    "set_identity",
    "find_company",
    "search",
    "get_filings",
]
