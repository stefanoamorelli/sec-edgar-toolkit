"""Type definitions for DEF 14A proxy statements parsing."""

from __future__ import annotations

from datetime import datetime
from typing import List, TypedDict


class CompensationItem(TypedDict):
    """Executive compensation item for a specific year."""

    year: int
    salary: float
    bonus: float
    stock_awards: float
    option_awards: float
    non_equity_incentive: float
    change_in_pension: float
    other_compensation: float
    total: float


class CompensationTable(TypedDict):
    """Executive compensation table."""

    name: str
    position: str
    compensation: List[CompensationItem]


class TopExecutive(TypedDict):
    """Top executive summary."""

    name: str
    position: str
    total_compensation: float


class CompensationSummary(TypedDict):
    """Executive compensation summary."""

    total_compensation: float
    median_compensation: float
    ceo_pay_ratio: float
    top_executives: List[TopExecutive]


class BoardMember(TypedDict):
    """Board member information."""

    name: str
    position: str
    tenure: int
    age: int
    independence: bool
    committees: List[str]
    other_directorships: List[str]
    compensation: float


class Proposal(TypedDict):
    """Shareholder proposal."""

    number: int
    title: str
    description: str
    type: str  # 'management', 'shareholder'
    recommendation: str  # 'for', 'against', 'abstain'
    details: str


class VotingMatter(TypedDict):
    """Voting matter results."""

    proposal: Proposal
    votes_for: int
    votes_against: int
    abstentions: int
    broker_non_votes: int
    outcome: str  # 'passed', 'failed', 'pending'


class ParsedProxyStatement(TypedDict):
    """Complete parsed proxy statement data."""

    form_type: str
    filing_date: datetime
    meeting_date: datetime
    cik: str
    company_name: str
    ticker: str
    executive_compensation: List[CompensationTable]
    compensation_summary: CompensationSummary
    board_members: List[BoardMember]
    proposals: List[Proposal]
    voting_matters: List[VotingMatter]
