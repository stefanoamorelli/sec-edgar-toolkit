"""Parser for financial forms (10-K, 10-Q) documents."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..types.financial_forms import (
    BalanceSheet,
    BalanceSheetItem,
    BusinessSegment,
    CashFlowItem,
    CashFlowStatement,
    FinancialMetrics,
    IncomeStatement,
    IncomeStatementItem,
    MDSection,
    ParsedFinancialForm,
    RiskFactor,
    XBRLFact,
)

logger = logging.getLogger(__name__)


class FinancialFormParser:
    """Parser for SEC financial forms (10-K, 10-Q)."""

    def __init__(self, raw_content: str) -> None:
        """
        Initialize the financial form parser.

        Args:
            raw_content: Raw content of the financial form
        """
        self.raw_content = raw_content

    def get_financial_statements(
        self,
    ) -> Dict[str, Union[BalanceSheet, IncomeStatement, CashFlowStatement]]:
        """
        Parse financial statements from the filing.

        Returns:
            Dictionary containing balance sheet, income statement, and cash flow statement
        """
        return {
            "balance_sheet": self.parse_balance_sheet(),
            "income_statement": self.parse_income_statement(),
            "cash_flow_statement": self.parse_cash_flow_statement(),
        }

    def parse_balance_sheet(self) -> BalanceSheet:
        """Parse balance sheet data."""
        balance_sheet_section = self._extract_section(
            r"BALANCE SHEET|CONSOLIDATED BALANCE SHEET"
        )

        return BalanceSheet(
            assets={
                "current_assets": self._extract_balance_sheet_items(
                    balance_sheet_section, r"current.*assets"
                ),
                "non_current_assets": self._extract_balance_sheet_items(
                    balance_sheet_section,
                    r"non.?current.*assets|property.*plant.*equipment",
                ),
                "total_assets": self._extract_balance_sheet_item(
                    balance_sheet_section, r"total.*assets"
                ),
            },
            liabilities={
                "current_liabilities": self._extract_balance_sheet_items(
                    balance_sheet_section, r"current.*liabilities"
                ),
                "non_current_liabilities": self._extract_balance_sheet_items(
                    balance_sheet_section, r"non.?current.*liabilities|long.?term.*debt"
                ),
                "total_liabilities": self._extract_balance_sheet_item(
                    balance_sheet_section, r"total.*liabilities"
                ),
            },
            equity={
                "total_equity": self._extract_balance_sheet_item(
                    balance_sheet_section, r"total.*equity|shareholders.*equity"
                ),
                "retained_earnings": self._extract_balance_sheet_item(
                    balance_sheet_section, r"retained.*earnings"
                ),
            },
        )

    def parse_income_statement(self) -> IncomeStatement:
        """Parse income statement data."""
        income_section = self._extract_section(
            r"INCOME STATEMENT|CONSOLIDATED STATEMENT.*OPERATIONS|STATEMENT.*EARNINGS"
        )

        return IncomeStatement(
            revenue=self._extract_income_statement_item(
                income_section, r"revenue|net.*sales|total.*revenue"
            ),
            gross_profit=self._extract_income_statement_item(
                income_section, r"gross.*profit|gross.*margin"
            ),
            operating_income=self._extract_income_statement_item(
                income_section, r"operating.*income|income.*from.*operations"
            ),
            net_income=self._extract_income_statement_item(
                income_section, r"net.*income|net.*earnings"
            ),
            earnings_per_share=self._extract_income_statement_item(
                income_section, r"earnings.*per.*share|basic.*earnings.*per.*share"
            ),
            operating_expenses=self._extract_income_statement_items(
                income_section,
                r"operating.*expenses|research.*development|sales.*marketing",
            ),
        )

    def parse_cash_flow_statement(self) -> CashFlowStatement:
        """Parse cash flow statement data."""
        cash_flow_section = self._extract_section(
            r"CASH FLOW|CONSOLIDATED STATEMENT.*CASH.*FLOW"
        )

        return CashFlowStatement(
            operating_activities=self._extract_cash_flow_items(
                cash_flow_section, r"operating.*activities|cash.*from.*operations"
            ),
            investing_activities=self._extract_cash_flow_items(
                cash_flow_section, r"investing.*activities|cash.*from.*investing"
            ),
            financing_activities=self._extract_cash_flow_items(
                cash_flow_section, r"financing.*activities|cash.*from.*financing"
            ),
            net_cash_flow=self._extract_cash_flow_item(
                cash_flow_section, r"net.*cash.*flow|net.*increase.*decrease.*cash"
            ),
        )

    def get_business_segments(self) -> List[BusinessSegment]:
        """Extract business segments information."""
        segment_section = self._extract_section(
            r"SEGMENT|BUSINESS.*SEGMENT|GEOGRAPHIC.*INFORMATION"
        )
        segments: List[BusinessSegment] = []

        # Extract segment data using pattern matching
        segment_pattern = re.compile(
            r"(\w+(?:\s+\w+)*)\s+segment.*?revenue.*?\$?([\d,]+)", re.IGNORECASE
        )

        for match in segment_pattern.finditer(segment_section):
            segments.append(
                BusinessSegment(
                    name=match.group(1).strip(),
                    revenue=self._parse_number(match.group(2)),
                    operating_income=0.0,  # Would need more sophisticated parsing
                    assets=0.0,  # Would need more sophisticated parsing
                    description="",
                )
            )

        return segments

    def get_risk_factors(self) -> List[RiskFactor]:
        """Extract risk factors."""
        risk_section = self._extract_section(r"RISK FACTORS|ITEM 1A")
        risk_factors: List[RiskFactor] = []

        # Split by common risk factor patterns
        factors = [
            factor.strip()
            for factor in re.split(r"(?=•|·|\d+\.|\n\n)", risk_section)
            if len(factor.strip()) > 50
        ]

        for factor in factors:
            severity = self._assess_risk_severity(factor)
            risk_factors.append(
                RiskFactor(
                    category=self._extract_risk_category(factor),
                    description=factor[:500],
                    severity=severity,
                )
            )

        return risk_factors[:10]  # Limit to top 10 risk factors

    def get_management_discussion(self) -> List[MDSection]:
        """Extract Management Discussion & Analysis sections."""
        mda_section = self._extract_section(r"MANAGEMENT.*DISCUSSION|ITEM 2|MD&A")
        sections: List[MDSection] = []

        # Split into subsections
        subsections = re.split(
            r"(?=OVERVIEW|RESULTS OF OPERATIONS|FINANCIAL CONDITION|LIQUIDITY)",
            mda_section,
            flags=re.IGNORECASE,
        )

        for section in subsections:
            if len(section.strip()) > 100:
                title = self._extract_section_title(section)
                sections.append(
                    MDSection(
                        title=title,
                        content=section.strip()[:1000],
                        key_metrics=self._extract_key_metrics(section),
                    )
                )

        return sections

    def get_xbrl_facts(self) -> List[XBRLFact]:
        """Extract XBRL facts (simplified version)."""
        xbrl_facts: List[XBRLFact] = []

        # Extract XBRL data if present
        xbrl_pattern = re.compile(
            r'<ix:nonFraction[^>]*name="([^"]*)"[^>]*contextRef="([^"]*)"[^>]*decimals="([^"]*)"[^>]*unitRef="([^"]*)"[^>]*>([^<]*)',
            re.IGNORECASE,
        )

        for match in xbrl_pattern.finditer(self.raw_content):
            xbrl_facts.append(
                XBRLFact(
                    name=match.group(1),
                    value=self._parse_number(match.group(5)),
                    units=match.group(4),
                    context_ref=match.group(2),
                    decimals=int(match.group(3)) if match.group(3).isdigit() else 0,
                    period=self._extract_period_from_context(match.group(2)),
                )
            )

        return xbrl_facts

    def get_financial_metrics(self) -> FinancialMetrics:
        """Calculate financial metrics."""
        balance_sheet = self.parse_balance_sheet()
        income_statement = self.parse_income_statement()

        return FinancialMetrics(
            market_cap=None,  # Would need stock price data
            pe_ratio=None,  # Would need stock price data
            debt_to_equity=self._calculate_debt_to_equity(balance_sheet),
            return_on_equity=self._calculate_roe(income_statement, balance_sheet),
            current_ratio=self._calculate_current_ratio(balance_sheet),
            quick_ratio=self._calculate_quick_ratio(balance_sheet),
        )

    def parse_all(self) -> ParsedFinancialForm:
        """Parse complete financial form."""
        header = self._parse_header()
        financial_statements = self.get_financial_statements()

        return ParsedFinancialForm(
            form_type=header["form_type"],
            filing_date=header["filing_date"],
            period_end_date=header["period_end_date"],
            cik=header["cik"],
            company_name=header["company_name"],
            ticker=header["ticker"],
            balance_sheet=financial_statements["balance_sheet"],
            income_statement=financial_statements["income_statement"],
            cash_flow_statement=financial_statements["cash_flow_statement"],
            business_segments=self.get_business_segments(),
            risk_factors=self.get_risk_factors(),
            management_discussion=self.get_management_discussion(),
            xbrl_facts=self.get_xbrl_facts(),
            financial_metrics=self.get_financial_metrics(),
        )

    # Helper methods

    def _extract_section(self, pattern: str) -> str:
        """Extract a section from the document using regex pattern."""
        match = re.search(pattern, self.raw_content, re.IGNORECASE)
        if not match:
            return ""

        start_index = match.start()
        end_index = self.raw_content.find("</DOCUMENT>", start_index)

        if end_index == -1:
            end_index = start_index + 50000

        return self.raw_content[start_index:end_index]

    def _extract_balance_sheet_items(
        self, section: str, pattern: str
    ) -> List[BalanceSheetItem]:
        """Extract balance sheet items matching the pattern."""
        items: List[BalanceSheetItem] = []
        regex = re.compile(pattern + r".*?\$([\\d,]+)", re.IGNORECASE)

        for match in regex.finditer(section):
            label = match.group(0).split("$")[0].strip()
            items.append(
                BalanceSheetItem(
                    label=label,
                    value=self._parse_number(match.group(1)),
                    units="USD",
                    period=self._extract_period(section),
                    filed=self._extract_filing_date(),
                )
            )

        return items

    def _extract_balance_sheet_item(
        self, section: str, pattern: str
    ) -> Optional[BalanceSheetItem]:
        """Extract a single balance sheet item."""
        items = self._extract_balance_sheet_items(section, pattern)
        return items[0] if items else None

    def _extract_income_statement_items(
        self, section: str, pattern: str
    ) -> List[IncomeStatementItem]:
        """Extract income statement items matching the pattern."""
        items: List[IncomeStatementItem] = []
        regex = re.compile(pattern + r".*?\$([\\d,]+)", re.IGNORECASE)

        for match in regex.finditer(section):
            label = match.group(0).split("$")[0].strip()
            items.append(
                IncomeStatementItem(
                    label=label,
                    value=self._parse_number(match.group(1)),
                    units="USD",
                    period=self._extract_period(section),
                    filed=self._extract_filing_date(),
                )
            )

        return items

    def _extract_income_statement_item(
        self, section: str, pattern: str
    ) -> Optional[IncomeStatementItem]:
        """Extract a single income statement item."""
        items = self._extract_income_statement_items(section, pattern)
        return items[0] if items else None

    def _extract_cash_flow_items(
        self, section: str, pattern: str
    ) -> List[CashFlowItem]:
        """Extract cash flow items matching the pattern."""
        items: List[CashFlowItem] = []
        regex = re.compile(pattern + r".*?\$([\\d,]+)", re.IGNORECASE)

        for match in regex.finditer(section):
            label = match.group(0).split("$")[0].strip()
            items.append(
                CashFlowItem(
                    label=label,
                    value=self._parse_number(match.group(1)),
                    units="USD",
                    period=self._extract_period(section),
                    filed=self._extract_filing_date(),
                )
            )

        return items

    def _extract_cash_flow_item(
        self, section: str, pattern: str
    ) -> Optional[CashFlowItem]:
        """Extract a single cash flow item."""
        items = self._extract_cash_flow_items(section, pattern)
        return items[0] if items else None

    def _parse_header(self) -> Dict[str, Any]:
        """Parse document header information."""
        cik_match = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", self.raw_content)
        company_match = re.search(
            r"COMPANY CONFORMED NAME:\s*([^\n\r]+)", self.raw_content
        )
        form_type_match = re.search(r"FORM TYPE:\s*([^\n\r]+)", self.raw_content)
        filing_date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", self.raw_content)
        period_match = re.search(
            r"CONFORMED PERIOD OF REPORT:\s*(\d{8})", self.raw_content
        )

        return {
            "cik": cik_match.group(1) if cik_match else "",
            "company_name": company_match.group(1).strip() if company_match else "",
            "form_type": form_type_match.group(1).strip() if form_type_match else "",
            "ticker": "",  # Would need to extract from trading symbol
            "filing_date": self._parse_date(
                filing_date_match.group(1) if filing_date_match else None
            ),
            "period_end_date": self._parse_date(
                period_match.group(1) if period_match else None
            ),
        }

    def _parse_number(self, value: str) -> float:
        """Parse number from string, removing commas and dollar signs."""
        return float(re.sub(r"[,$]", "", value)) if value else 0.0

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date from YYYYMMDD format."""
        if not date_str:
            return datetime.now()

        # Parse YYYYMMDD format
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])

        return datetime(year, month, day)

    def _extract_period(self, section: str) -> str:
        """Extract period from section."""
        period_match = re.search(r"(\d{4})", section)
        return period_match.group(1) if period_match else str(datetime.now().year)

    def _extract_filing_date(self) -> datetime:
        """Extract filing date from document."""
        date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", self.raw_content)
        return self._parse_date(date_match.group(1) if date_match else None)

    def _assess_risk_severity(self, risk_text: str) -> str:
        """Assess risk severity based on keywords."""
        high_risk_keywords = [
            "material adverse",
            "significant risk",
            "substantial risk",
            "could result in",
        ]
        medium_risk_keywords = ["may affect", "potential impact", "could impact"]

        text = risk_text.lower()

        if any(keyword in text for keyword in high_risk_keywords):
            return "high"
        elif any(keyword in text for keyword in medium_risk_keywords):
            return "medium"

        return "low"

    def _extract_risk_category(self, risk_text: str) -> str:
        """Extract risk category based on keywords."""
        categories = [
            {
                "keywords": ["market", "competition", "customer"],
                "category": "Market Risk",
            },
            {
                "keywords": ["regulation", "compliance", "legal"],
                "category": "Regulatory Risk",
            },
            {
                "keywords": ["technology", "cyber", "security"],
                "category": "Technology Risk",
            },
            {
                "keywords": ["financial", "credit", "liquidity"],
                "category": "Financial Risk",
            },
            {
                "keywords": ["operational", "supply chain", "manufacturing"],
                "category": "Operational Risk",
            },
        ]

        text = risk_text.lower()

        for cat in categories:
            if any(keyword in text for keyword in cat["keywords"]):
                return cat["category"]

        return "General Risk"

    def _extract_section_title(self, section: str) -> str:
        """Extract section title from text."""
        lines = section.split("\n")
        for line in lines[:5]:
            if 10 < len(line.strip()) < 100:
                return line.strip()
        return "Management Discussion"

    def _extract_key_metrics(self, section: str) -> List[Dict[str, str]]:
        """Extract key metrics from section."""
        metrics: List[Dict[str, str]] = []

        # Extract percentage changes
        change_pattern = re.compile(
            r"(\w+(?:\s+\w+)*)\s+(?:increased|decreased|changed)\s+by\s+([\d.]+%)",
            re.IGNORECASE,
        )

        for match in change_pattern.finditer(section):
            metrics.append(
                {
                    "metric": match.group(1).strip(),
                    "value": "",
                    "change": match.group(2),
                }
            )

        return metrics[:5]

    def _extract_period_from_context(self, context_ref: str) -> str:
        """Extract period from context reference."""
        period_match = re.search(r"(\d{4})", context_ref)
        return period_match.group(1) if period_match else str(datetime.now().year)

    def _calculate_debt_to_equity(self, balance_sheet: BalanceSheet) -> Optional[float]:
        """Calculate debt-to-equity ratio."""
        total_liabilities = balance_sheet["liabilities"]["total_liabilities"]
        total_equity = balance_sheet["equity"]["total_equity"]

        if (
            total_liabilities
            and total_equity
            and total_liabilities["value"]
            and total_equity["value"]
            and total_equity["value"] != 0
        ):
            return total_liabilities["value"] / total_equity["value"]

        return None

    def _calculate_roe(
        self, income_statement: IncomeStatement, balance_sheet: BalanceSheet
    ) -> Optional[float]:
        """Calculate return on equity."""
        net_income = income_statement["net_income"]
        total_equity = balance_sheet["equity"]["total_equity"]

        if (
            net_income
            and total_equity
            and net_income["value"]
            and total_equity["value"]
            and total_equity["value"] != 0
        ):
            return net_income["value"] / total_equity["value"]

        return None

    def _calculate_current_ratio(self, balance_sheet: BalanceSheet) -> Optional[float]:
        """Calculate current ratio."""
        current_assets = sum(
            asset["value"] for asset in balance_sheet["assets"]["current_assets"]
        )
        current_liabilities = sum(
            liability["value"]
            for liability in balance_sheet["liabilities"]["current_liabilities"]
        )

        if current_assets and current_liabilities and current_liabilities != 0:
            return current_assets / current_liabilities

        return None

    def _calculate_quick_ratio(self, balance_sheet: BalanceSheet) -> Optional[float]:
        """Calculate quick ratio (simplified)."""
        # Simplified calculation - would need more sophisticated asset classification
        current_assets = sum(
            asset["value"] for asset in balance_sheet["assets"]["current_assets"]
        )
        current_liabilities = sum(
            liability["value"]
            for liability in balance_sheet["liabilities"]["current_liabilities"]
        )

        if current_assets and current_liabilities and current_liabilities != 0:
            return (
                current_assets * 0.8
            ) / current_liabilities  # Approximate quick ratio

        return None
