"""Type definitions for financial forms (10-K, 10-Q) parsing."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TypedDict, Union


class BalanceSheetItem(TypedDict):
    """Balance sheet line item."""

    label: str
    value: float
    units: str
    period: str
    filed: datetime


class BalanceSheetAssets(TypedDict):
    """Balance sheet assets section."""

    current_assets: List[BalanceSheetItem]
    non_current_assets: List[BalanceSheetItem]
    total_assets: Optional[BalanceSheetItem]


class BalanceSheetLiabilities(TypedDict):
    """Balance sheet liabilities section."""

    current_liabilities: List[BalanceSheetItem]
    non_current_liabilities: List[BalanceSheetItem]
    total_liabilities: Optional[BalanceSheetItem]


class BalanceSheetEquity(TypedDict):
    """Balance sheet equity section."""

    total_equity: Optional[BalanceSheetItem]
    retained_earnings: Optional[BalanceSheetItem]


class BalanceSheet(TypedDict):
    """Parsed balance sheet data."""

    assets: BalanceSheetAssets
    liabilities: BalanceSheetLiabilities
    equity: BalanceSheetEquity


class IncomeStatementItem(TypedDict):
    """Income statement line item."""

    label: str
    value: float
    units: str
    period: str
    filed: datetime


class IncomeStatement(TypedDict):
    """Parsed income statement data."""

    revenue: Optional[IncomeStatementItem]
    gross_profit: Optional[IncomeStatementItem]
    operating_income: Optional[IncomeStatementItem]
    net_income: Optional[IncomeStatementItem]
    earnings_per_share: Optional[IncomeStatementItem]
    operating_expenses: List[IncomeStatementItem]


class CashFlowItem(TypedDict):
    """Cash flow statement line item."""

    label: str
    value: float
    units: str
    period: str
    filed: datetime


class CashFlowStatement(TypedDict):
    """Parsed cash flow statement data."""

    operating_activities: List[CashFlowItem]
    investing_activities: List[CashFlowItem]
    financing_activities: List[CashFlowItem]
    net_cash_flow: Optional[CashFlowItem]


class BusinessSegment(TypedDict):
    """Business segment information."""

    name: str
    revenue: float
    operating_income: float
    assets: float
    description: str


class RiskFactor(TypedDict):
    """Risk factor information."""

    category: str
    description: str
    severity: str  # 'low', 'medium', 'high'


class KeyMetric(TypedDict):
    """Key metric from MD&A section."""

    metric: str
    value: str
    change: str


class MDSection(TypedDict):
    """Management Discussion & Analysis section."""

    title: str
    content: str
    key_metrics: List[KeyMetric]


class XBRLFact(TypedDict):
    """XBRL fact data."""

    name: str
    value: Union[float, str]
    units: str
    context_ref: str
    decimals: int
    period: str


class FinancialMetrics(TypedDict):
    """Calculated financial metrics."""

    market_cap: Optional[float]
    pe_ratio: Optional[float]
    debt_to_equity: Optional[float]
    return_on_equity: Optional[float]
    current_ratio: Optional[float]
    quick_ratio: Optional[float]


class ParsedFinancialForm(TypedDict):
    """Complete parsed financial form data."""

    form_type: str
    filing_date: datetime
    period_end_date: datetime
    cik: str
    company_name: str
    ticker: str
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    business_segments: List[BusinessSegment]
    risk_factors: List[RiskFactor]
    management_discussion: List[MDSection]
    xbrl_facts: List[XBRLFact]
    financial_metrics: FinancialMetrics
