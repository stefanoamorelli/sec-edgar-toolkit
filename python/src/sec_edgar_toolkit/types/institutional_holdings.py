"""Type definitions for 13F institutional holdings parsing."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TypedDict


class SharesOrPrincipalAmount(TypedDict):
    """Shares or principal amount information."""

    shares: float
    principal: float
    type: str  # 'SH', 'PRN'


class VotingAuthority(TypedDict):
    """Voting authority information."""

    sole: int
    shared: int
    none: int


class Holding(TypedDict):
    """Individual holding information."""

    name_of_issuer: str
    title_of_class: str
    cusip: str
    value: float
    shares_or_principal_amount: SharesOrPrincipalAmount
    put_call: Optional[str]  # 'Put', 'Call', None
    investment_discretion: str  # 'SOLE', 'SHARED', 'NONE'
    manager_class: str
    voting_authority: VotingAuthority


class PortfolioSummary(TypedDict):
    """Portfolio summary statistics."""

    total_value: float
    total_positions: int
    top_sector_allocation: str
    concentration_ratio: float
    average_position_size: float


class Position(TypedDict):
    """Individual position with portfolio weight."""

    holding: Holding
    portfolio_weight: float
    rank: int


class SectorAllocation(TypedDict):
    """Sector allocation information."""

    sector: str
    value: float
    percentage: float
    number_of_holdings: int


class HoldingComparison(TypedDict):
    """Comparison between two holdings periods."""

    holding: str
    cusip: str
    previous_value: float
    current_value: float
    change_in_value: float
    change_in_shares: float
    action: str  # 'NEW', 'SOLD_OUT', 'INCREASED', 'DECREASED', 'NO_CHANGE'


class ParsedInstitutionalHolding(TypedDict):
    """Complete parsed institutional holding data."""

    form_type: str
    filing_date: datetime
    period_of_report: datetime
    cik: str
    manager_name: str
    holdings: List[Holding]
    portfolio_summary: PortfolioSummary
    sector_allocations: List[SectorAllocation]
