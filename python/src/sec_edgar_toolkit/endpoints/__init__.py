"""SEC EDGAR API endpoint implementations."""

from .company import CompanyEndpoints
from .filings import FilingsEndpoints
from .fulltext import FullTextSearchEndpoints
from .xbrl import XbrlEndpoints

__all__ = [
    "CompanyEndpoints",
    "FilingsEndpoints",
    "FullTextSearchEndpoints",
    "XbrlEndpoints",
]
