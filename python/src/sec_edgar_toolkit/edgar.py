"""
SEC EDGAR API client with fluent interface design.

This module provides a comprehensive toolkit for accessing and analyzing
SEC filing data through a chainable API interface.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from .client import SecEdgarApi
from .core import Filing as CoreFiling
from .types import CompanyTicker

logger = logging.getLogger(__name__)


class EdgarClient:
    """
    SEC EDGAR API client with fluent interface design.

    This client provides comprehensive access to SEC filing data through
    a chainable, type-safe API with intelligent caching and rate limiting.

    Example:
        >>> client = EdgarClient("MyApp/1.0 (contact@example.com)")
        >>> company = client.companies.lookup("AAPL")
        >>> filings = company.filings.filter(form_types=["10-K"]).limit(5).fetch()
    """

    def __init__(self, user_agent: str, **kwargs: Any) -> None:
        """
        Initialize Edgar client.

        Args:
            user_agent: Required user agent with contact information
            **kwargs: Additional configuration options
        """
        self._api = SecEdgarApi(user_agent=user_agent, **kwargs)
        self.companies = CompanyQueryBuilder(self._api)
        self.filings = FilingQueryBuilder(self._api)
        self.facts = FactsQueryBuilder(self._api)

    def configure(self, **settings: Any) -> EdgarClient:
        """
        Configure client settings with method chaining.

        Args:
            **settings: Configuration options

        Returns:
            Self for method chaining
        """
        # Could update internal settings here
        return self


class CompanyQueryBuilder:
    """Fluent interface for company queries."""

    def __init__(self, api: SecEdgarApi) -> None:
        self._api = api

    def lookup(self, identifier: Union[str, int]) -> Optional[Company]:
        """
        Look up a single company by ticker or CIK.

        Args:
            identifier: Ticker symbol or CIK number

        Returns:
            Company object if found

        Example:
            >>> company = client.companies.lookup("AAPL")
        """
        # Try as ticker first
        if isinstance(identifier, str) and not identifier.isdigit():
            data = self._api.get_company_by_ticker(identifier)
            if data:
                return Company(data, self._api)

        # Try as CIK
        cik = str(identifier).zfill(10) if str(identifier).isdigit() else None
        if cik:
            data = self._api.get_company_by_cik(cik)
            if data:
                return Company(data, self._api)

        return None

    def search(self, query: str) -> CompanySearchBuilder:
        """
        Search for companies with fluent interface.

        Args:
            query: Search query

        Returns:
            CompanySearchBuilder for further filtering

        Example:
            >>> results = client.companies.search("Apple").limit(5).execute()
        """
        return CompanySearchBuilder(self._api, query)

    def batch_lookup(
        self, identifiers: List[Union[str, int]]
    ) -> List[Optional[Company]]:
        """
        Look up multiple companies in batch.

        Args:
            identifiers: List of ticker symbols or CIKs

        Returns:
            List of Company objects (None for not found)

        Example:
            >>> companies = client.companies.batch_lookup(["AAPL", "MSFT", "GOOGL"])
        """
        return [self.lookup(identifier) for identifier in identifiers]


class CompanySearchBuilder:
    """Builder for company search queries."""

    def __init__(self, api: SecEdgarApi, query: str) -> None:
        self._api = api
        self._query = query
        self._limit: Optional[int] = None

    def limit(self, count: int) -> CompanySearchBuilder:
        """Limit number of results."""
        self._limit = count
        return self

    def execute(self) -> List[Company]:
        """Execute the search query."""
        results = self._api.search_companies(self._query)
        companies = [Company(data, self._api) for data in results]

        if self._limit:
            return companies[: self._limit]
        return companies


class FilingQueryBuilder:
    """Fluent interface for filing queries."""

    def __init__(self, api: SecEdgarApi) -> None:
        self._api = api

    def for_company(self, company: Union[Company, str, int]) -> CompanyFilingBuilder:
        """
        Get filings for a specific company.

        Args:
            company: Company object, ticker, or CIK

        Returns:
            CompanyFilingBuilder for further filtering

        Example:
            >>> filings = client.filings.for_company("AAPL").form_types(["10-K"]).recent(5).fetch()
        """
        if isinstance(company, Company):
            cik = company.cik
        else:
            # Look up company to get CIK
            comp = CompanyQueryBuilder(self._api).lookup(company)
            if not comp:
                raise ValueError(f"Company not found: {company}")
            cik = comp.cik

        return CompanyFilingBuilder(self._api, cik)


class CompanyFilingBuilder:
    """Builder for company filing queries."""

    def __init__(self, api: SecEdgarApi, cik: str) -> None:
        self._api = api
        self._cik = cik
        self._form_types: Optional[List[str]] = None
        self._since: Optional[str] = None
        self._until: Optional[str] = None
        self._limit: Optional[int] = None

    def form_types(self, forms: List[str]) -> CompanyFilingBuilder:
        """Filter by form types."""
        self._form_types = forms
        return self

    def since(self, date: str) -> CompanyFilingBuilder:
        """Filter filings since date (YYYY-MM-DD)."""
        self._since = date
        return self

    def until(self, date: str) -> CompanyFilingBuilder:
        """Filter filings until date (YYYY-MM-DD)."""
        self._until = date
        return self

    def recent(self, count: int) -> CompanyFilingBuilder:
        """Limit to most recent filings."""
        self._limit = count
        return self

    def fetch(self) -> List[Filing]:
        """Execute the query and fetch filings."""
        # Get submissions
        submission_type = (
            self._form_types[0]
            if self._form_types and len(self._form_types) == 1
            else None
        )

        submissions = self._api.get_company_submissions(
            self._cik,
            submission_type=submission_type,
            from_date=self._since,
            to_date=self._until,
        )

        filings = []
        recent_filings = submissions.get("filings", {}).get("recent", {})

        if recent_filings:
            accession_numbers = recent_filings.get("accessionNumber", [])
            form_list = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])

            for i, accession in enumerate(accession_numbers):
                if i >= len(form_list) or i >= len(filing_dates):
                    break

                form_type = form_list[i]
                filing_date = filing_dates[i]

                # Filter by form types if specified
                if self._form_types and form_type not in self._form_types:
                    continue

                filing_data = {
                    "cik": self._cik,
                    "accession_number": accession,
                    "form_type": form_type,
                    "filing_date": filing_date,
                }

                filing = Filing(filing_data, self._api)
                filings.append(filing)

                if self._limit and len(filings) >= self._limit:
                    break

        return filings


class FactsQueryBuilder:
    """Fluent interface for XBRL facts queries."""

    def __init__(self, api: SecEdgarApi) -> None:
        self._api = api

    def for_company(self, company: Union[Company, str, int]) -> CompanyFactsBuilder:
        """
        Get facts for a specific company.

        Args:
            company: Company object, ticker, or CIK

        Returns:
            CompanyFactsBuilder for further querying

        Example:
            >>> facts = client.facts.for_company("AAPL").concept("Assets").in_units("USD").fetch()
        """
        if isinstance(company, Company):
            cik = company.cik
        else:
            # Look up company to get CIK
            comp = CompanyQueryBuilder(self._api).lookup(company)
            if not comp:
                raise ValueError(f"Company not found: {company}")
            cik = comp.cik

        return CompanyFactsBuilder(self._api, cik)


class CompanyFactsBuilder:
    """Builder for company facts queries."""

    def __init__(self, api: SecEdgarApi, cik: str) -> None:
        self._api = api
        self._cik = cik
        self._concept: Optional[str] = None
        self._taxonomy: str = "us-gaap"
        self._units: Optional[str] = None
        self._period: Optional[str] = None

    def concept(self, concept_name: str) -> CompanyFactsBuilder:
        """Filter by specific concept."""
        self._concept = concept_name
        return self

    def taxonomy(self, taxonomy_name: str) -> CompanyFactsBuilder:
        """Specify taxonomy (default: us-gaap)."""
        self._taxonomy = taxonomy_name
        return self

    def in_units(self, units: str) -> CompanyFactsBuilder:
        """Filter by units (e.g., USD, shares)."""
        self._units = units
        return self

    def period(self, period_filter: str) -> CompanyFactsBuilder:
        """Filter by period."""
        self._period = period_filter
        return self

    def fetch(self) -> List[Dict[str, Any]]:
        """Execute the query and fetch facts."""
        if self._concept:
            data = self._api.get_company_concept(
                self._cik, self._taxonomy, self._concept, self._units
            )
            return self._process_concept_data(data)
        else:
            facts = self._api.get_company_facts(self._cik)
            return self._process_all_facts(facts)

    def _process_concept_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process concept-specific data."""
        results = []
        units = data.get("units", {})

        for unit, unit_data in units.items():
            if self._units and unit != self._units:
                continue

            for fact in unit_data:
                if self._period:
                    fact_period = (
                        fact.get("fy") or fact.get("fp") or fact.get("frame", "")
                    )
                    if self._period not in str(fact_period):
                        continue

                fact_record = {
                    "concept": self._concept,
                    "value": fact.get("val"),
                    "unit": unit,
                    "period": fact.get("frame")
                    or f"FY{fact.get('fy', '')}{fact.get('fp', '')}",
                    "fiscal_year": fact.get("fy"),
                    "fiscal_period": fact.get("fp"),
                    "filed": fact.get("filed"),
                    "form": fact.get("form"),
                }
                results.append(fact_record)

        return results

    def _process_all_facts(self, facts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process all facts data."""
        # Simplified - would implement full processing here
        return []


class Company:
    """
    Comprehensive company representation with fluent interface design.

    This class provides rich access to company data, filings, and financial
    information through an intuitive, chainable API.
    """

    def __init__(self, data: CompanyTicker, api: SecEdgarApi) -> None:
        self._data = data
        self._api = api
        self.cik = data["cik_str"]
        self.ticker = data.get("ticker", "")
        self.name = data["title"]
        self.exchange = data.get("exchange", "")

    @property
    def filings(self) -> CompanyFilingBuilder:
        """Get filings builder for this company."""
        return CompanyFilingBuilder(self._api, self.cik)

    @property
    def facts(self) -> CompanyFactsBuilder:
        """Get facts builder for this company."""
        return CompanyFactsBuilder(self._api, self.cik)

    def get_latest_filing(self, form_type: str = "10-K") -> Optional[Filing]:
        """
        Get the most recent filing of a specific type.

        Args:
            form_type: Type of form to retrieve

        Returns:
            Most recent filing or None

        Example:
            >>> latest_10k = company.get_latest_filing("10-K")
        """
        filings = self.filings.form_types([form_type]).recent(1).fetch()
        return filings[0] if filings else None

    def financial_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key financial metrics.

        Returns:
            Dictionary with key financial data

        Example:
            >>> summary = company.financial_summary()
            >>> print(f"Assets: ${summary['total_assets']:,.0f}")
        """
        key_concepts = ["Assets", "Liabilities", "StockholdersEquity", "Revenues"]
        summary = {}

        for concept in key_concepts:
            facts = self.facts.concept(concept).in_units("USD").fetch()
            if facts:
                latest = max(facts, key=lambda x: x.get("filed", ""))
                summary[f"total_{concept.lower()}"] = latest.get("value")

        return summary

    def __str__(self) -> str:
        return (
            f"{self.ticker}: {self.name}"
            if self.ticker
            else f"CIK {self.cik}: {self.name}"
        )

    def __repr__(self) -> str:
        return f"Company(ticker='{self.ticker}', cik='{self.cik}', name='{self.name}')"


class Filing:
    """
    Comprehensive filing representation with advanced content processing.

    This class provides rich access to SEC filing content, structured data
    extraction, and financial analysis capabilities.
    """

    def __init__(self, data: Dict[str, Any], api: SecEdgarApi) -> None:
        self._data = data
        self._api = api
        self.cik = data["cik"]
        self.accession_number = data["accession_number"]
        self.form_type = data["form_type"]
        self.filing_date = data["filing_date"]

        # Create core filing for content access
        self._core_filing = CoreFiling(
            cik=self.cik,
            accession_number=self.accession_number,
            form_type=self.form_type,
            filing_date=self.filing_date,
            api=api,
        )

    @property
    def content(self) -> FilingContentAccess:
        """Get content access interface."""
        return FilingContentAccess(self._core_filing)

    @property
    def analysis(self) -> FilingAnalysis:
        """Get analysis interface."""
        return FilingAnalysis(self._core_filing)

    def preview(self, length: int = 500) -> str:
        """
        Get a preview of the filing content.

        Args:
            length: Number of characters to preview

        Returns:
            Preview text
        """
        try:
            text = self._core_filing.text()
            return text[:length] + "..." if len(text) > length else text
        except Exception:
            return "Content preview not available"

    def __str__(self) -> str:
        return f"{self.form_type} filing for {self.cik} on {self.filing_date}"

    def __repr__(self) -> str:
        return f"Filing(form='{self.form_type}', cik='{self.cik}', date='{self.filing_date}')"


class FilingContentAccess:
    """Interface for accessing filing content."""

    def __init__(self, core_filing: CoreFiling) -> None:
        self._core_filing = core_filing

    def as_text(self, clean: bool = True) -> str:
        """Get filing as plain text."""
        return self._core_filing.text("text" if clean else "raw")

    def as_html(self) -> str:
        """Get filing as HTML."""
        return self._core_filing.text("html")

    def as_structured_data(self) -> Dict[str, Any]:
        """Get filing as structured data."""
        return self._core_filing.obj()

    def download_url(self) -> str:
        """Get direct download URL."""
        return self._core_filing.url


class FilingAnalysis:
    """Interface for filing analysis and extraction."""

    def __init__(self, core_filing: CoreFiling) -> None:
        self._core_filing = core_filing

    def extract_financials(self) -> Optional[FinancialData]:
        """Extract financial data if available."""
        if self._core_filing.form_type in ["10-K", "10-Q"]:
            xbrl = self._core_filing.xbrl()
            return FinancialData(xbrl)
        return None

    def extract_key_metrics(self) -> Dict[str, Any]:
        """Extract key business metrics."""
        try:
            structured = self._core_filing.obj()
            # Extract relevant metrics based on form type
            if self._core_filing.form_type == "8-K":
                return structured.get("current_events", {})
            elif self._core_filing.form_type in ["3", "4", "5"]:
                return {
                    "insider_transactions": len(
                        structured.get("non_derivative_transactions", [])
                    ),
                    "holdings": len(structured.get("non_derivative_holdings", [])),
                }
            return {}
        except Exception:
            return {}


class FinancialData:
    """Enhanced financial data interface."""

    def __init__(self, xbrl_instance: Any) -> None:
        self._xbrl = xbrl_instance

    def balance_sheet(self) -> Optional[Dict[str, Any]]:
        """Get balance sheet data."""
        return self._xbrl.find_statement("balance_sheet")

    def income_statement(self) -> Optional[Dict[str, Any]]:
        """Get income statement data."""
        return self._xbrl.find_statement("income_statement")

    def cash_flow(self) -> Optional[Dict[str, Any]]:
        """Get cash flow statement data."""
        return self._xbrl.find_statement("cash_flow")

    def key_ratios(self) -> Dict[str, Optional[float]]:
        """Calculate key financial ratios."""
        ratios = {}

        try:
            assets = self._xbrl.get_concept_value("Assets")
            liabilities = self._xbrl.get_concept_value("Liabilities")
            equity = self._xbrl.get_concept_value("StockholdersEquity")

            if assets and liabilities:
                ratios["debt_to_assets"] = liabilities / assets
            if liabilities and equity:
                ratios["debt_to_equity"] = liabilities / equity

        except Exception:
            pass

        return ratios


# Convenience functions for backward compatibility
def create_client(user_agent: str, **kwargs: Any) -> EdgarClient:
    """
    Create an Edgar client instance.

    Args:
        user_agent: Required user agent with contact information
        **kwargs: Additional configuration options

    Returns:
        EdgarClient instance

    Example:
        >>> client = create_client("MyApp/1.0 (contact@example.com)")
    """
    return EdgarClient(user_agent, **kwargs)


# Async support for modern applications
class AsyncEdgarClient:
    """Async version of the Edgar client."""

    def __init__(self, user_agent: str, **kwargs: Any) -> None:
        self._client = EdgarClient(user_agent, **kwargs)

    async def lookup_company(self, identifier: Union[str, int]) -> Optional[Company]:
        """Async company lookup."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._client.companies.lookup, identifier
        )

    async def search_companies(
        self, query: str, limit: Optional[int] = None
    ) -> List[Company]:
        """Async company search."""
        builder = self._client.companies.search(query)
        if limit:
            builder = builder.limit(limit)

        return await asyncio.get_event_loop().run_in_executor(None, builder.execute)

    @asynccontextmanager
    async def batch_operations(self) -> AsyncGenerator[AsyncEdgarClient, None]:
        """Context manager for batch operations."""
        yield self
