"""
SEC EDGAR Toolkit - toolkit for accessing SEC EDGAR filing data.

Three layers, from most to least convenient:

1. Object API (primary): ``Company``, ``Filing``, and module-level helpers

       from sec_edgar_toolkit import Company, set_identity

       set_identity("MyApp/1.0 (me@example.com)")
       apple = Company("AAPL")
       latest_10k = apple.get_filings(form="10-K").latest()

2. Fluent client: chainable query builders

       from sec_edgar_toolkit import create_client

       client = create_client("MyApp/1.0 (me@example.com)")
       apple = client.companies.lookup("AAPL")

3. Low-level client: raw SEC JSON endpoints

       from sec_edgar_toolkit import SecEdgarApi

       api = SecEdgarApi(user_agent="MyApp/1.0 (me@example.com)")
       facts = api.get_company_facts("0000320193")
"""

__version__ = "0.2.0"

# Object API - primary interface
# Stable alias for the object API import surface
from . import compat, core

# Low-level API client
from .client.sec_edgar_api import SecEdgarApi
from .core import (
    Attachment,
    Company,
    CompanyFacts,
    EightK,
    EightKItem,
    FactQuery,
    Filing,
    FilingItem,
    Filings,
    Financials,
    Holding13F,
    OwnershipForm,
    OwnershipHolding,
    OwnershipTransaction,
    TenK,
    TenKItem,
    TenQ,
    TenQItem,
    ThirteenF,
    XBRLInstance,
    find_company,
    full_text_search,
    get_current_filings,
    get_filings,
    search,
    search_filings,
    set_identity,
)

# Fluent client (the fluent Company/Filing classes live in .edgar)
from .edgar import (
    AsyncEdgarClient,
    EdgarClient,
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
    ThirteenFParser,
    TwentyFItem,
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
    # Object API
    "Company",
    "Filing",
    "Filings",
    "CompanyFacts",
    "Financials",
    "XBRLInstance",
    "FactQuery",
    "OwnershipForm",
    "OwnershipTransaction",
    "OwnershipHolding",
    "EightK",
    "TenK",
    "TenQ",
    "Attachment",
    "FilingItem",
    "TenKItem",
    "TenQItem",
    "ThirteenF",
    "Holding13F",
    "EightKItem",
    "set_identity",
    "find_company",
    "search",
    "get_filings",
    "get_current_filings",
    "full_text_search",
    "search_filings",
    # Fluent client
    "EdgarClient",
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
    "ThirteenFParser",
    "TwentyFItem",
    # Types
    "CompanyTicker",
    "FilingDocument",
    "FilingDetail",
    "CompanySubmissions",
    # Namespaces
    "core",
    "compat",
]
