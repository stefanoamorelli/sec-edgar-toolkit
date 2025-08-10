"""SEC EDGAR Toolkit - Advanced toolkit for accessing SEC EDGAR filing data."""

__version__ = "0.1.0"

# Main fluent API - primary interface
# Low-level API client
from .client.sec_edgar_api import SecEdgarApi
from .edgar import (
    AsyncEdgarClient,
    Company,
    EdgarClient,
    Filing,
    create_client,
)

# Exception classes
from .exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SecEdgarApiError,
)

# XML Parsers for specialized use cases
from .parsers import (
    Form4Parser,
    Form5Parser,
    OwnershipFormParser,
)

# Type definitions
from .types import (
    CompanySubmissions,
    CompanyTicker,
    FilingDetail,
    FilingDocument,
)

__all__ = [
    "__version__",
    # Main fluent API
    "EdgarClient",
    "Company",
    "Filing",
    "create_client",
    "AsyncEdgarClient",
    # Low-level API client
    "SecEdgarApi",
    # Exception classes
    "SecEdgarApiError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    # Parsers
    "OwnershipFormParser",
    "Form4Parser",
    "Form5Parser",
    # Types
    "CompanyTicker",
    "FilingDocument",
    "FilingDetail",
    "CompanySubmissions",
]
