"""
Company class providing edgartools-compatible API.

This class represents a company and provides methods to access its filings,
financial data, and other information from the SEC database.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..client import SecEdgarApi
from ..types import CompanyTicker

if TYPE_CHECKING:
    from .filing import Filing

logger = logging.getLogger(__name__)


class Company:
    """
    Represents a company with SEC filings.

    This class provides an edgartools-compatible interface for working with
    company data and filings.

    Attributes:
        cik: Company's Central Index Key
        name: Company name
        ticker: Stock ticker symbol
        exchange: Stock exchange
        sic: Standard Industrial Classification code
        ein: Employer Identification Number
        address: Company address information
    """

    def __init__(
        self,
        identifier: Union[str, int],
        api: Optional[SecEdgarApi] = None,
        _company_data: Optional[CompanyTicker] = None,
    ) -> None:
        """
        Initialize a Company object.

        Args:
            identifier: Company CIK, ticker, or name
            api: SEC Edgar API client instance
            _company_data: Pre-loaded company data (internal use)
        """
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self._company_data = _company_data
        self._submissions_cache: Optional[Dict[str, Any]] = None
        self._facts_cache: Optional[Dict[str, Any]] = None

        # If we don't have company data, try to find it
        if _company_data is None:
            self._load_company_data(identifier)

        # Set attributes from company data
        if self._company_data:
            self.cik = self._company_data["cik_str"]
            self.name = self._company_data["title"]
            self.ticker = self._company_data.get("ticker", "")
            self.exchange = self._company_data.get("exchange", "")
        else:
            # Fallback if company not found
            self.cik = str(identifier).zfill(10) if str(identifier).isdigit() else ""
            self.name = ""
            self.ticker = ""
            self.exchange = ""

        # Additional attributes that will be loaded on demand
        self.sic: Optional[str] = None
        self.ein: Optional[str] = None
        self.address: Optional[Dict[str, Any]] = None

    def _load_company_data(self, identifier: Union[str, int]) -> None:
        """Load company data from the API."""
        # Try as ticker first
        if isinstance(identifier, str) and not identifier.isdigit():
            self._company_data = self._api.get_company_by_ticker(identifier)

        # Try as CIK if ticker failed
        if self._company_data is None:
            cik = str(identifier).zfill(10) if str(identifier).isdigit() else None
            if cik:
                self._company_data = self._api.get_company_by_cik(cik)

    def __getattr__(self, name: str) -> Any:
        """
        Dynamic attribute access for company metadata.

        This allows accessing any field from the company submissions data
        using dot notation, similar to edgartools.
        """
        # Load submissions data if not cached
        if self._submissions_cache is None:
            try:
                self._submissions_cache = self._api.get_company_submissions(self.cik)
            except Exception as e:
                logger.warning(f"Failed to load company submissions: {e}")
                self._submissions_cache = {}

        # Check if the attribute exists in submissions data
        if name in self._submissions_cache:
            return self._submissions_cache[name]

        # Check common aliases
        field_mapping = {
            "business_address": "addresses",
            "mailing_address": "addresses",
            "sic_description": "sicDescription",
            "state_of_incorporation": "stateOfIncorporation",
            "fiscal_year_end": "fiscalYearEnd",
        }

        mapped_field = field_mapping.get(name)
        if mapped_field and mapped_field in self._submissions_cache:
            return self._submissions_cache[mapped_field]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def get_filings(
        self,
        form: Optional[Union[str, List[str]]] = None,
        since: Optional[str] = None,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List["Filing"]:
        """
        Get filings for this company.

        Args:
            form: Form type(s) to filter by (e.g., "10-K", ["10-K", "10-Q"])
            since: Start date (YYYY-MM-DD format)
            before: End date (YYYY-MM-DD format)
            limit: Maximum number of filings to return

        Returns:
            List of Filing objects

        Example:
            >>> company = Company("AAPL")
            >>> filings = company.get_filings(form="10-K", limit=5)
        """
        # Import here to avoid circular imports
        from .filing import Filing

        # Convert form to submission type filter
        submission_type = None
        if form:
            if isinstance(form, str):
                submission_type = form
            elif len(form) == 1:
                submission_type = form[0]

        # Get submissions data
        submissions = self._api.get_company_submissions(
            self.cik, submission_type=submission_type, from_date=since, to_date=before
        )

        filings = []
        recent_filings = submissions.get("filings", {}).get("recent", {})

        if recent_filings:
            accession_numbers = recent_filings.get("accessionNumber", [])
            form_list = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])

            # Convert form to list for filtering
            form_types = []
            if form:
                if isinstance(form, str):
                    form_types = [form]
                else:
                    form_types = list(form)

            for i, accession in enumerate(accession_numbers):
                if i >= len(form_list) or i >= len(filing_dates):
                    break

                filing_form = form_list[i]
                filing_date = filing_dates[i]

                # Filter by form types if specified
                if form_types and filing_form not in form_types:
                    continue

                filing = Filing(
                    cik=self.cik,
                    accession_number=accession,
                    form_type=filing_form,
                    filing_date=filing_date,
                    api=self._api,
                )
                filings.append(filing)

                if limit and len(filings) >= limit:
                    break

        return filings

    def get_company_facts(self) -> Dict[str, Any]:
        """
        Get XBRL facts data for this company.

        Returns:
            Dictionary containing company facts organized by taxonomy

        Example:
            >>> company = Company("AAPL")
            >>> facts = company.get_company_facts()
            >>> gaap_facts = facts['facts']['us-gaap']
        """
        if self._facts_cache is None:
            self._facts_cache = self._api.get_company_facts(self.cik)
        return self._facts_cache

    def get_concept(
        self,
        taxonomy: str,
        tag: str,
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get specific XBRL concept data for this company.

        Args:
            taxonomy: Taxonomy name (e.g., 'us-gaap', 'dei')
            tag: XBRL tag name (e.g., 'Assets', 'Revenues')
            unit: Unit of measurement (e.g., 'USD', 'shares')

        Returns:
            Historical data for the specified concept

        Example:
            >>> company = Company("AAPL")
            >>> assets = company.get_concept("us-gaap", "Assets", "USD")
        """
        return self._api.get_company_concept(self.cik, taxonomy, tag, unit)

    def __str__(self) -> str:
        """String representation of the company."""
        if self.ticker:
            return f"{self.ticker}: {self.name}"
        return f"CIK {self.cik}: {self.name}"

    def __repr__(self) -> str:
        """Detailed string representation of the company."""
        return f"Company(cik='{self.cik}', ticker='{self.ticker}', name='{self.name}')"
