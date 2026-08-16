"""
Stable import surface for the high-level API.

The package root exports the fluent client (``EdgarClient``); this module
exposes the object-style API (``Company`` / ``Filing`` / ``set_identity``
and friends) under one import path:

    from sec_edgar_toolkit.compat import Company, set_identity

    set_identity("MyApp/1.0 (contact@example.com)")
    company = Company("AAPL")
    latest = company.get_filings(form="10-K").latest()
"""

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

__all__ = [
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
]
