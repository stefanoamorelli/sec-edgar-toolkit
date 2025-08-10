"""Company-related type definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class CompanyTicker(TypedDict):
    """Type definition for company ticker information."""

    cik_str: str
    ticker: str
    title: str
    exchange: Optional[str]


class CompanySubmissions(TypedDict):
    """Type definition for company submissions response."""

    cik: str
    entityType: str
    sic: Optional[str]
    sicDescription: Optional[str]
    insiderTransactionForOwnerExists: bool
    insiderTransactionForIssuerExists: bool
    name: str
    tickers: List[str]
    exchanges: List[str]
    ein: Optional[str]
    description: Optional[str]
    website: Optional[str]
    investorWebsite: Optional[str]
    category: Optional[str]
    fiscalYearEnd: Optional[str]
    stateOfIncorporation: Optional[str]
    stateOfIncorporationDescription: Optional[str]
    addresses: Dict[str, Any]
    phone: Optional[str]
    flags: Optional[str]
    formerNames: List[Dict[str, str]]
    filings: Dict[str, Any]
