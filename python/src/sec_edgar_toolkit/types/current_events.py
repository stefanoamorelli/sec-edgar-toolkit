"""Type definitions for 8-K current events parsing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict


class Event(TypedDict):
    """Current event information."""

    type: str
    description: str
    date: datetime
    item: str
    significance: str  # 'low', 'medium', 'high'
    details: Dict[str, Any]


class Agreement(TypedDict):
    """Material agreement information."""

    type: str
    parties: List[str]
    effective_date: datetime
    description: str
    value: Optional[float]
    currency: str


class PersonInfo(TypedDict):
    """Person information for executive changes."""

    name: str
    position: str
    previous_position: Optional[str]


class CompensationInfo(TypedDict):
    """Compensation information."""

    salary: float
    bonus: float
    equity: float


class ExecutiveChange(TypedDict):
    """Executive change information."""

    type: str  # 'appointment', 'resignation', 'termination'
    person: PersonInfo
    effective_date: datetime
    reason: Optional[str]
    compensation: Optional[CompensationInfo]


class AcquisitionTarget(TypedDict):
    """Acquisition target information."""

    name: str
    description: str


class Acquisition(TypedDict):
    """Acquisition information."""

    type: str  # 'acquisition', 'merger', 'divestiture'
    target: AcquisitionTarget
    value: Optional[float]
    currency: str
    expected_closing_date: Optional[datetime]
    status: str  # 'announced', 'pending', 'completed', 'terminated'


class GuidanceItem(TypedDict):
    """Earnings guidance item."""

    metric: str
    value: str


class EarningsData(TypedDict):
    """Earnings data information."""

    period: str
    revenue: Optional[float]
    net_income: Optional[float]
    earnings_per_share: Optional[float]
    guidance: List[GuidanceItem]


class ParsedCurrentEvent(TypedDict):
    """Complete parsed current event data."""

    form_type: str
    filing_date: datetime
    cik: str
    company_name: str
    ticker: str
    events: List[Event]
    material_agreements: List[Agreement]
    executive_changes: List[ExecutiveChange]
    acquisitions: List[Acquisition]
    earnings_results: Optional[EarningsData]
