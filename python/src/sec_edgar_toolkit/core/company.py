"""
Company class of the high-level API.

Represents a company and provides access to its filings, financial data,
and profile information from the SEC database.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..client import SecEdgarApi
from ..types import CompanyTicker
from .collections import Filings
from .facts import CompanyFacts
from .financials import Financials

if TYPE_CHECKING:
    from .filing import Filing

logger = logging.getLogger(__name__)


class Company:
    """
    Represents a company with SEC filings.

    Attributes:
        cik: Company's Central Index Key (10-digit, zero-padded)
        name: Company name
        ticker: Stock ticker symbol
        exchange: Stock exchange

    Profile fields from the submissions data (``sic``, ``sic_description``,
    ``state_of_incorporation``, ``fiscal_year_end``, ``ein``, ...) are
    available as attributes and loaded on first access.
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
            api: SEC EDGAR API client instance
            _company_data: Pre-loaded company data (internal use)
        """
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self._company_data = _company_data
        self._submissions_cache: Optional[Dict[str, Any]] = None
        self._facts_cache: Optional[CompanyFacts] = None

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
            # Fall back to treating a numeric identifier as a CIK; other
            # companies (e.g. filers without a listed ticker) still resolve
            # through the submissions API.
            if str(identifier).isdigit():
                self.cik = str(identifier).zfill(10)
            else:
                raise ValueError(f"Company not found: {identifier}")
            self.ticker = ""
            self.exchange = ""
            self.name = ""
            submissions = self._get_submissions()
            if not submissions:
                raise ValueError(f"Company not found: {identifier}")
            self.name = submissions.get("name", "")
            tickers = submissions.get("tickers") or []
            self.ticker = tickers[0] if tickers else ""
            exchanges = submissions.get("exchanges") or []
            self.exchange = exchanges[0] if exchanges else ""

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

    def _get_submissions(self) -> Dict[str, Any]:
        """Load (and cache) the company submissions data."""
        if self._submissions_cache is None:
            try:
                self._submissions_cache = self._api.get_company_submissions(self.cik)
            except Exception as e:
                logger.warning(f"Failed to load company submissions: {e}")
                self._submissions_cache = {}
        return self._submissions_cache

    @property
    def tickers(self) -> List[str]:
        """All ticker symbols for this company."""
        submissions = self._get_submissions()
        tickers = submissions.get("tickers") or []
        if tickers:
            return tickers
        return [self.ticker] if self.ticker else []

    def __getattr__(self, name: str) -> Any:
        """
        Dynamic attribute access for company profile metadata,
        backed by the submissions data.
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        submissions = self._get_submissions()

        if name in submissions:
            return submissions[name]

        # Common snake_case aliases
        field_mapping = {
            "business_address": "addresses",
            "mailing_address": "addresses",
            "address": "addresses",
            "sic_description": "sicDescription",
            "state_of_incorporation": "stateOfIncorporation",
            "state": "stateOfIncorporation",
            "fiscal_year_end": "fiscalYearEnd",
            "entity_type": "entityType",
        }

        mapped_field = field_mapping.get(name)
        if mapped_field and mapped_field in submissions:
            return submissions[mapped_field]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def get_filings(
        self,
        form: Optional[Union[str, List[str]]] = None,
        since: Optional[str] = None,
        before: Optional[str] = None,
        limit: Optional[int] = None,
        deep: bool = False,
    ) -> Filings:
        """
        Get filings for this company, newest first.

        Args:
            form: Form type(s) to filter by (e.g., "10-K", ["10-K", "10-Q"])
            since: Start date (YYYY-MM-DD format)
            before: End date (YYYY-MM-DD format)
            limit: Maximum number of filings to return
            deep: Also walk the older-history pages beyond the ~1000 most
                recent filings (one extra request per page)

        Returns:
            Filings collection (list-like, with ``.latest()``)

        Example:
            >>> company = Company("AAPL")
            >>> filings = company.get_filings(form="10-K", limit=5)
            >>> latest = filings.latest()
        """
        submissions = self._api.get_company_submissions(
            self.cik, from_date=since, to_date=before
        )

        form_types: List[str] = []
        if form:
            form_types = [form] if isinstance(form, str) else list(form)

        filings = Filings()
        filings_data = submissions.get("filings", {})

        self._append_filings(filings, filings_data.get("recent", {}), form_types, limit)

        if deep and not (limit and len(filings) >= limit):
            for page in filings_data.get("files", []):
                if since and page.get("filingTo", "") < since:
                    continue
                try:
                    page_data = self._api.get_company_submissions_page(page["name"])
                except Exception as e:
                    logger.warning(f"Failed to fetch submissions page: {e}")
                    continue
                self._append_filings(filings, page_data, form_types, limit)
                if limit and len(filings) >= limit:
                    break

        return filings

    def _append_filings(
        self,
        filings: Filings,
        columns: Dict[str, Any],
        form_types: List[str],
        limit: Optional[int],
    ) -> None:
        """Append Filing objects built from one columnar filings payload."""
        # Import here to avoid circular imports
        from .filing import Filing

        if not columns:
            return

        accession_numbers = columns.get("accessionNumber", [])
        form_list = columns.get("form", [])
        filing_dates = columns.get("filingDate", [])
        file_numbers = columns.get("fileNumber", [])
        acceptance_datetimes = columns.get("acceptanceDateTime", [])
        report_dates = columns.get("reportDate", [])
        primary_documents = columns.get("primaryDocument", [])
        sizes = columns.get("size", [])

        def column(values: List[Any], index: int) -> Any:
            return values[index] if index < len(values) else ""

        for i, accession in enumerate(accession_numbers):
            if i >= len(form_list) or i >= len(filing_dates):
                break

            filing_form = form_list[i]
            if form_types and filing_form not in form_types:
                continue

            filings.append(
                Filing(
                    cik=self.cik,
                    accession_number=accession,
                    form_type=filing_form,
                    filing_date=filing_dates[i],
                    api=self._api,
                    company_name=self.name,
                    file_number=column(file_numbers, i),
                    acceptance_datetime=column(acceptance_datetimes, i),
                    period_of_report=column(report_dates, i),
                    primary_document=column(primary_documents, i),
                    size=column(sizes, i),
                )
            )

            if limit and len(filings) >= limit:
                break

    def get_facts(self) -> CompanyFacts:
        """
        Get XBRL facts for this company.

        Returns:
            CompanyFacts (``.data`` mapping plus ``get_fact(concept)``)

        Example:
            >>> company = Company("AAPL")
            >>> facts = company.get_facts()
            >>> revenue = facts.get_fact("Revenues")
        """
        if self._facts_cache is None:
            self._facts_cache = CompanyFacts(self._api.get_company_facts(self.cik))
        return self._facts_cache

    def get_company_facts(self) -> Dict[str, Any]:
        """Get the raw XBRL company-facts payload."""
        return self.get_facts()._raw

    def get_financials(self) -> Financials:
        """Annual financial statements (from 10-K facts)."""
        return Financials(self.get_facts()._raw, form_type="10-K")

    def get_quarterly_financials(self) -> Financials:
        """Quarterly financial statements (from 10-Q facts)."""
        return Financials(self.get_facts()._raw, form_type="10-Q")

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
