"""Type definitions for cross-form analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, TypedDict


class TimelineEvent(TypedDict):
    """Timeline event information."""

    date: datetime
    type: str  # 'filing', 'insider_transaction', 'institutional_change', 'earnings', 'announcement'
    form_type: str
    description: str
    significance: str  # 'low', 'medium', 'high'
    details: Dict[str, Any]


class TimelinePeriod(TypedDict):
    """Timeline period information."""

    start: datetime
    end: datetime


class Timeline(TypedDict):
    """Company timeline data."""

    cik: str
    company_name: str
    events: List[TimelineEvent]
    period: TimelinePeriod


class DataPoint(TypedDict):
    """Correlation data point."""

    date: datetime
    value1: float
    value2: float


class Correlation(TypedDict):
    """Correlation analysis result."""

    type: str  # 'insider_trading_vs_earnings', 'insider_trading_vs_announcements', 'institutional_vs_performance'
    strength: float
    significance: float
    description: str
    data_points: List[DataPoint]


class OwnershipData(TypedDict):
    """Ownership data for a period."""

    previous: float
    current: float
    change: float


class MajorShareholder(TypedDict):
    """Major shareholder information."""

    name: str
    type: str  # 'institutional', 'insider', 'other'
    ownership: float
    change: float


class OwnershipChange(TypedDict):
    """Ownership change information."""

    period: str
    institutional_ownership: OwnershipData
    insider_ownership: OwnershipData
    major_shareholders: List[MajorShareholder]


class OwnershipTrends(TypedDict):
    """Ownership trend indicators."""

    institutional_trend: str  # 'increasing', 'decreasing', 'stable'
    insider_trend: str  # 'increasing', 'decreasing', 'stable'
    concentration: str  # 'increasing', 'decreasing', 'stable'


class OwnershipTrend(TypedDict):
    """Ownership trend analysis."""

    cik: str
    company_name: str
    changes: List[OwnershipChange]
    trends: OwnershipTrends


class FilingCompliance(TypedDict):
    """Filing compliance metrics."""

    on_time: int
    late: int
    missed: int
    score: float


class InsiderCompliance(TypedDict):
    """Insider compliance metrics."""

    form4_on_time: int
    form4_late: int
    form5_filed: int
    score: float


class CompliancePeriod(TypedDict):
    """Compliance period information."""

    start: datetime
    end: datetime


class ComplianceMetrics(TypedDict):
    """Compliance metrics analysis."""

    cik: str
    company_name: str
    period: CompliancePeriod
    filing_compliance: FilingCompliance
    insider_compliance: InsiderCompliance
    overall_score: float
    risk_level: str  # 'low', 'medium', 'high'
