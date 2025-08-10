"""SEC EDGAR API endpoint implementations."""

from .company import CompanyEndpoints
from .filings import FilingsEndpoints
from .xbrl import XbrlEndpoints

__all__ = [
    "CompanyEndpoints",
    "FilingsEndpoints",
    "XbrlEndpoints",
]
