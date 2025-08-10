"""
XBRL instance class providing edgartools-compatible API.

This class represents an XBRL instance and provides methods to query
financial data, extract statements, and convert to various formats.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from ..client import SecEdgarApi

logger = logging.getLogger(__name__)


class XBRLInstance:
    """
    Represents an XBRL instance with financial data.

    This class provides an edgartools-compatible interface for working with
    XBRL data, including querying facts, extracting financial statements,
    and converting data to various formats.

    Attributes:
        filing: Associated Filing object
        cik: Company's Central Index Key
        facts: XBRL facts data
    """

    def __init__(
        self,
        filing: Filing,
        api: Optional[SecEdgarApi] = None,
    ) -> None:
        """
        Initialize an XBRL instance.

        Args:
            filing: Filing object this XBRL instance belongs to
            api: SEC Edgar API client instance
        """
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self.filing = filing
        self.cik = filing.cik

        # Cache for XBRL data
        self._facts: Optional[Dict[str, Any]] = None
        self._us_gaap_facts: Optional[Dict[str, Any]] = None
        self._dei_facts: Optional[Dict[str, Any]] = None

    @property
    def facts(self) -> Dict[str, Any]:
        """Get all XBRL facts for the company."""
        if self._facts is None:
            self._facts = self._api.get_company_facts(self.cik)
        return self._facts

    @property
    def us_gaap(self) -> Dict[str, Any]:
        """Get US-GAAP facts."""
        if self._us_gaap_facts is None:
            facts = self.facts
            self._us_gaap_facts = facts.get("facts", {}).get("us-gaap", {})
        return self._us_gaap_facts

    @property
    def dei(self) -> Dict[str, Any]:
        """Get DEI (Document Entity Information) facts."""
        if self._dei_facts is None:
            facts = self.facts
            self._dei_facts = facts.get("facts", {}).get("dei", {})
        return self._dei_facts

    def query(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
        period: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Query XBRL facts with filtering.

        Args:
            concept: XBRL concept/tag name (e.g., "Assets", "Revenues")
            taxonomy: Taxonomy to search in ("us-gaap", "dei", etc.)
            unit: Unit filter (e.g., "USD", "shares")
            period: Period filter (e.g., "2023", "CY2023Q4")
            **kwargs: Additional filters

        Returns:
            List of matching XBRL facts

        Example:
            >>> xbrl = filing.xbrl()
            >>> assets = xbrl.query(concept="Assets", unit="USD")
        """
        results = []

        # Get facts for the specified taxonomy
        if taxonomy == "us-gaap":
            taxonomy_facts = self.us_gaap
        elif taxonomy == "dei":
            taxonomy_facts = self.dei
        else:
            taxonomy_facts = self.facts.get("facts", {}).get(taxonomy, {})

        # If concept is specified, filter to that concept
        if concept:
            if concept in taxonomy_facts:
                concept_data = taxonomy_facts[concept]
                results.extend(
                    self._process_concept_data(concept, concept_data, unit, period)
                )
        else:
            # Query all concepts
            for concept_name, concept_data in taxonomy_facts.items():
                results.extend(
                    self._process_concept_data(concept_name, concept_data, unit, period)
                )

        return results

    def _process_concept_data(
        self,
        concept_name: str,
        concept_data: Dict[str, Any],
        unit_filter: Optional[str],
        period_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Process concept data and apply filters."""
        results = []

        units = concept_data.get("units", {})
        for unit, unit_data in units.items():
            # Apply unit filter
            if unit_filter and unit != unit_filter:
                continue

            for fact in unit_data:
                # Apply period filter
                if period_filter:
                    fact_period = (
                        fact.get("fy") or fact.get("fp") or fact.get("frame", "")
                    )
                    if period_filter not in str(fact_period):
                        continue

                # Create standardized fact record
                fact_record = {
                    "concept": concept_name,
                    "taxonomy": "us-gaap",  # Default, could be enhanced
                    "value": fact.get("val"),
                    "unit": unit,
                    "period": fact.get("frame")
                    or f"FY{fact.get('fy', '')}{fact.get('fp', '')}",
                    "fiscal_year": fact.get("fy"),
                    "fiscal_period": fact.get("fp"),
                    "start_date": fact.get("start"),
                    "end_date": fact.get("end"),
                    "filed": fact.get("filed"),
                    "accession_number": fact.get("accn"),
                    "form": fact.get("form"),
                }
                results.append(fact_record)

        return results

    def find_statement(
        self,
        statement_type: str = "balance_sheet",
        period: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find and extract a specific financial statement.

        Args:
            statement_type: Type of statement ("balance_sheet", "income_statement", "cash_flow")
            period: Period filter (e.g., "2023", "CY2023Q4")

        Returns:
            Dictionary containing the financial statement data

        Example:
            >>> xbrl = filing.xbrl()
            >>> balance_sheet = xbrl.find_statement("balance_sheet")
        """
        if statement_type == "balance_sheet":
            return self._extract_balance_sheet(period)
        elif statement_type == "income_statement":
            return self._extract_income_statement(period)
        elif statement_type == "cash_flow":
            return self._extract_cash_flow_statement(period)
        else:
            logger.warning(f"Unknown statement type: {statement_type}")
            return None

    def _extract_balance_sheet(self, period: Optional[str]) -> Dict[str, Any]:
        """Extract balance sheet data."""
        # Key balance sheet concepts
        concepts = [
            "Assets",
            "AssetsCurrent",
            "AssetsNoncurrent",
            "Liabilities",
            "LiabilitiesCurrent",
            "LiabilitiesNoncurrent",
            "StockholdersEquity",
            "RetainedEarningsAccumulatedDeficit",
        ]

        statement_data = {}
        for concept in concepts:
            facts = self.query(concept=concept, unit="USD", period=period)
            if facts:
                # Get most recent fact
                latest_fact = max(facts, key=lambda x: x.get("filed", ""))
                statement_data[concept] = latest_fact

        return {
            "statement_type": "balance_sheet",
            "period": period,
            "data": statement_data,
        }

    def _extract_income_statement(self, period: Optional[str]) -> Dict[str, Any]:
        """Extract income statement data."""
        # Key income statement concepts
        concepts = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "CostOfRevenue",
            "GrossProfit",
            "OperatingIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
        ]

        statement_data = {}
        for concept in concepts:
            facts = self.query(concept=concept, unit="USD", period=period)
            if facts:
                # Get most recent fact
                latest_fact = max(facts, key=lambda x: x.get("filed", ""))
                statement_data[concept] = latest_fact

        return {
            "statement_type": "income_statement",
            "period": period,
            "data": statement_data,
        }

    def _extract_cash_flow_statement(self, period: Optional[str]) -> Dict[str, Any]:
        """Extract cash flow statement data."""
        # Key cash flow concepts
        concepts = [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInFinancingActivities",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ]

        statement_data = {}
        for concept in concepts:
            facts = self.query(concept=concept, unit="USD", period=period)
            if facts:
                # Get most recent fact
                latest_fact = max(facts, key=lambda x: x.get("filed", ""))
                statement_data[concept] = latest_fact

        return {
            "statement_type": "cash_flow",
            "period": period,
            "data": statement_data,
        }

    def to_dataframe(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Convert XBRL data to pandas DataFrame.

        Args:
            concept: Specific concept to include
            taxonomy: Taxonomy to use
            unit: Unit filter

        Returns:
            DataFrame with XBRL facts

        Example:
            >>> xbrl = filing.xbrl()
            >>> df = xbrl.to_dataframe(concept="Assets", unit="USD")
        """
        if not PANDAS_AVAILABLE:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            )

        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit)
        return pd.DataFrame(facts)

    def to_dict(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert XBRL data to dictionary format.

        Args:
            concept: Specific concept to include
            taxonomy: Taxonomy to use
            unit: Unit filter

        Returns:
            Dictionary with XBRL facts

        Example:
            >>> xbrl = filing.xbrl()
            >>> data = xbrl.to_dict(concept="Assets", unit="USD")
        """
        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit)
        return {
            "metadata": {
                "cik": self.cik,
                "filing_date": self.filing.filing_date,
                "form_type": self.filing.form_type,
            },
            "facts": facts,
        }

    def get_concept_value(
        self,
        concept: str,
        taxonomy: str = "us-gaap",
        unit: str = "USD",
        period: Optional[str] = None,
    ) -> Optional[float]:
        """
        Get a single value for a specific concept.

        Args:
            concept: XBRL concept name
            taxonomy: Taxonomy to search in
            unit: Unit of measurement
            period: Period filter

        Returns:
            Single numeric value or None if not found

        Example:
            >>> xbrl = filing.xbrl()
            >>> total_assets = xbrl.get_concept_value("Assets")
        """
        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit, period=period)
        if facts:
            # Return the most recent value
            latest_fact = max(facts, key=lambda x: x.get("filed", ""))
            return latest_fact.get("value")
        return None

    def list_concepts(self, taxonomy: str = "us-gaap") -> List[str]:
        """
        List all available concepts in a taxonomy.

        Args:
            taxonomy: Taxonomy to list concepts from

        Returns:
            List of concept names

        Example:
            >>> xbrl = filing.xbrl()
            >>> concepts = xbrl.list_concepts("us-gaap")
        """
        if taxonomy == "us-gaap":
            return list(self.us_gaap.keys())
        elif taxonomy == "dei":
            return list(self.dei.keys())
        else:
            facts = self.facts.get("facts", {})
            return list(facts.get(taxonomy, {}).keys())

    def __str__(self) -> str:
        """String representation of the XBRL instance."""
        return f"XBRL instance for {self.filing.form_type} filing (CIK: {self.cik})"

    def __repr__(self) -> str:
        """Detailed string representation of the XBRL instance."""
        return f"XBRLInstance(cik='{self.cik}', form='{self.filing.form_type}', date='{self.filing.filing_date}')"


# Import at the end to avoid circular imports
from .filing import Filing
