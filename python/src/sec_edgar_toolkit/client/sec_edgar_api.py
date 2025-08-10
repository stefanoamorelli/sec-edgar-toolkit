"""
SEC EDGAR API Client.

This module provides the main SEC EDGAR API client that combines all endpoint
modules into a single, easy-to-use interface.

Example:
    Basic usage of the SEC EDGAR API client::

        from sec_edgar_toolkit import SecEdgarApi

        # Initialize client with your user agent
        api = SecEdgarApi(user_agent="MyCompany/1.0 (contact@example.com)")

        # Search for company by ticker
        company = api.get_company_by_ticker("AAPL")
        print(f"Apple Inc. CIK: {company['cik_str']}")

        # Get recent filings
        submissions = api.get_company_submissions(company['cik_str'])

Note:
    The SEC requires a User-Agent header with contact information for all API requests.
    Please provide accurate contact information in case the SEC needs to reach you
    about your usage.

See Also:
    - SEC EDGAR API Documentation: https://www.sec.gov/edgar/sec-api-documentation
    - Rate Limits: 10 requests per second per IP address
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union

from ..endpoints import CompanyEndpoints, FilingsEndpoints, XbrlEndpoints
from ..types import CompanyTicker
from ..utils import HttpClient

# Configure module logger
logger = logging.getLogger(__name__)


class SecEdgarApi:
    """
    SEC EDGAR API client for accessing SEC filing data.

    This client provides methods to interact with all SEC EDGAR API endpoints,
    including company searches, filing retrievals, and submissions data.

    The client implements automatic rate limiting to comply with SEC's 10 requests
    per second limit and includes retry logic for transient failures.

    Attributes:
        company: Company information endpoints
        filings: Filing data endpoints
        xbrl: XBRL data endpoints

    Args:
        user_agent: Required user agent string with contact information
        rate_limit_delay: Delay between requests in seconds (default: 0.1)
        max_retries: Maximum number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 30)

    Raises:
        ValueError: If user_agent is not provided or is invalid

    Example:
        >>> api = SecEdgarApi("MyApp/1.0 (email@example.com)")
        >>> api.get_company_by_ticker("MSFT")
        {'cik_str': '0000789019', 'ticker': 'MSFT', 'title': 'MICROSOFT CORP'}
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        rate_limit_delay: float = 0.1,
        max_retries: int = 3,
        timeout: int = 30,
    ) -> None:
        """
        Initialize SEC EDGAR API client.

        Args:
            user_agent: User agent string with contact info (required by SEC).
                       If not provided, will be read from SEC_EDGAR_TOOLKIT_USER_AGENT environment variable.
            rate_limit_delay: Minimum delay between requests in seconds
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds

        Raises:
            ValueError: If user_agent is empty or doesn't contain contact info
            EnvironmentError: If SEC_EDGAR_TOOLKIT_USER_AGENT environment variable is not set when user_agent is None
        """
        # Get user agent from parameter or environment variable
        if user_agent is None:
            user_agent = os.getenv("SEC_EDGAR_TOOLKIT_USER_AGENT")
            if not user_agent:
                raise OSError(
                    "SEC_EDGAR_TOOLKIT_USER_AGENT environment variable is required when user_agent parameter is not provided. "
                    "Set SEC_EDGAR_TOOLKIT_USER_AGENT in your environment or .env file with format: 'CompanyName/Version (contact@email.com)'"
                )

        if not user_agent or len(user_agent) < 10:
            raise ValueError(
                "User-Agent is required and must include contact information. "
                "Format: 'CompanyName/Version (contact@email.com)'"
            )

        # Store configuration
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout

        # Initialize HTTP client
        self.http_client = HttpClient(
            user_agent=user_agent,
            rate_limit_delay=rate_limit_delay,
            max_retries=max_retries,
            timeout=timeout,
        )

        # Initialize endpoint modules
        self.company = CompanyEndpoints(self.http_client)
        self.filings = FilingsEndpoints(self.http_client)
        self.xbrl = XbrlEndpoints(self.http_client)

        logger.info(f"SEC EDGAR API client initialized with User-Agent: {user_agent}")

    # Company information methods (delegate to company endpoints)
    def get_company_tickers(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get all company tickers with CIK mappings."""
        return self.company.get_company_tickers(force_refresh)

    def get_company_by_ticker(self, ticker: str) -> Optional[CompanyTicker]:
        """Get company information by ticker symbol."""
        return self.company.get_company_by_ticker(ticker)

    def get_company_by_cik(self, cik: Union[str, int]) -> Optional[CompanyTicker]:
        """Get company information by CIK (Central Index Key)."""
        return self.company.get_company_by_cik(cik)

    def search_companies(self, query: str) -> List[Any]:
        """Search for companies by name."""
        return self.company.search_companies(query)

    # Filing methods (delegate to filings endpoints)
    def get_company_submissions(
        self,
        cik: Union[str, int],
        submission_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all submissions for a specific company."""
        return self.filings.get_company_submissions(
            cik, submission_type, from_date, to_date
        )

    def get_filing(
        self,
        cik: Union[str, int],
        accession_number: str,
    ) -> Dict[str, Any]:
        """Get specific filing details and documents."""
        return self.filings.get_filing(cik, accession_number)

    # XBRL methods (delegate to xbrl endpoints)
    def get_company_facts(self, cik: Union[str, int]) -> Dict[str, Any]:
        """Get XBRL facts data for a company."""
        return self.xbrl.get_company_facts(cik)

    def get_company_concept(
        self,
        cik: Union[str, int],
        taxonomy: str,
        tag: str,
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get specific XBRL concept data for a company."""
        return self.xbrl.get_company_concept(cik, taxonomy, tag, unit)

    def get_frames(
        self,
        taxonomy: str,
        tag: str,
        unit: str,
        year: int,
        quarter: Optional[int] = None,
        instantaneous: bool = False,
    ) -> Dict[str, Any]:
        """Get aggregated XBRL data for all companies for a specific period."""
        return self.xbrl.get_frames(taxonomy, tag, unit, year, quarter, instantaneous)
