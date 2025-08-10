"""Company information endpoints."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

from ..types import CompanyTicker
from ..utils import HttpClient


class CompanyEndpoints:
    """
    Endpoints for company information and lookup.

    This class handles all company-related API endpoints including:
    - Company ticker lookup
    - CIK (Central Index Key) resolution
    - Company search functionality
    - Company tickers data with caching

    Args:
        http_client: HTTP client instance for making requests

    Example:
        >>> client = HttpClient("MyApp/1.0 (contact@example.com)")
        >>> endpoints = CompanyEndpoints(client)
        >>> company = endpoints.get_company_by_ticker("AAPL")
    """

    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"

    def __init__(self, http_client: HttpClient) -> None:
        """Initialize company endpoints."""
        self.http_client = http_client
        self._company_tickers_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None

    def get_company_tickers(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get all company tickers with CIK mappings.

        This method fetches the complete list of companies with their tickers,
        CIKs, and exchange information. The data is cached for 24 hours by default.

        Args:
            force_refresh: Force refresh of cached data

        Returns:
            Dictionary with 'data' key containing list of company information

        Example:
            >>> tickers = endpoints.get_company_tickers()
            >>> apple = next(c for c in tickers['data'] if c['ticker'] == 'AAPL')
            >>> print(apple['cik_str'])
            '0000320193'
        """
        # Check cache validity (24 hours)
        if (
            not force_refresh
            and self._company_tickers_cache is not None
            and self._cache_timestamp is not None
            and (time.time() - self._cache_timestamp) < 86400
        ):
            return self._company_tickers_cache

        data = self.http_client.get(self.COMPANY_TICKERS_URL)

        # Cache the data
        self._company_tickers_cache = data
        self._cache_timestamp = time.time()

        return data

    def get_company_by_ticker(self, ticker: str) -> Optional[CompanyTicker]:
        """
        Get company information by ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

        Returns:
            Company information including CIK, or None if not found

        Example:
            >>> company = endpoints.get_company_by_ticker("GOOGL")
            >>> print(f"{company['title']} - CIK: {company['cik_str']}")
        """
        ticker = ticker.upper()
        tickers_data = self.get_company_tickers()

        fields = tickers_data.get("fields", [])
        if not fields:
            return None

        # Find field indices
        try:
            cik_idx = fields.index("cik")
            name_idx = fields.index("name")
            ticker_idx = fields.index("ticker")
            exchange_idx = fields.index("exchange")
        except ValueError:
            return None

        for company_data in tickers_data.get("data", []):
            if (
                len(company_data) > max(cik_idx, name_idx, ticker_idx, exchange_idx)
                and company_data[ticker_idx] == ticker
            ):
                # Convert to our expected format
                return {
                    "cik_str": str(company_data[cik_idx]).zfill(10),
                    "ticker": company_data[ticker_idx],
                    "title": company_data[name_idx],
                    "exchange": company_data[exchange_idx]
                    if exchange_idx < len(company_data)
                    else None,
                }  # type: ignore[no-any-return]

        return None

    def get_company_by_cik(self, cik: Union[str, int]) -> Optional[CompanyTicker]:
        """
        Get company information by CIK (Central Index Key).

        Args:
            cik: Company CIK number (can be string or int)

        Returns:
            Company information, or None if not found

        Example:
            >>> company = endpoints.get_company_by_cik("0000320193")
            >>> print(company['title'])  # Apple Inc.
        """
        # Normalize CIK for comparison (remove leading zeros)
        target_cik = int(str(cik).lstrip("0")) if str(cik).strip() else 0
        tickers_data = self.get_company_tickers()

        fields = tickers_data.get("fields", [])
        if not fields:
            return None

        # Find field indices
        try:
            cik_idx = fields.index("cik")
            name_idx = fields.index("name")
            ticker_idx = fields.index("ticker")
            exchange_idx = fields.index("exchange")
        except ValueError:
            return None

        for company_data in tickers_data.get("data", []):
            if (
                len(company_data) > max(cik_idx, name_idx, ticker_idx, exchange_idx)
                and company_data[cik_idx] == target_cik
            ):
                # Convert to our expected format
                return {
                    "cik_str": str(company_data[cik_idx]).zfill(10),
                    "ticker": company_data[ticker_idx],
                    "title": company_data[name_idx],
                    "exchange": company_data[exchange_idx]
                    if exchange_idx < len(company_data)
                    else None,
                }  # type: ignore[no-any-return]

        return None

    def search_companies(self, query: str) -> List[CompanyTicker]:
        """
        Search for companies by name.

        Args:
            query: Search query (partial company name)

        Returns:
            List of matching companies

        Example:
            >>> results = endpoints.search_companies("Apple")
            >>> for company in results:
            ...     print(f"{company['ticker']}: {company['title']}")
        """
        query = query.lower()
        tickers_data = self.get_company_tickers()
        results: List[CompanyTicker] = []

        fields = tickers_data.get("fields", [])
        if not fields:
            return results

        # Find field indices
        try:
            cik_idx = fields.index("cik")
            name_idx = fields.index("name")
            ticker_idx = fields.index("ticker")
            exchange_idx = fields.index("exchange")
        except ValueError:
            return results

        for company_data in tickers_data.get("data", []):
            if len(company_data) > max(cik_idx, name_idx, ticker_idx, exchange_idx):
                company_name = company_data[name_idx].lower()
                if query in company_name:
                    # Convert to our expected format
                    company_dict: CompanyTicker = {
                        "cik_str": str(company_data[cik_idx]).zfill(10),
                        "ticker": company_data[ticker_idx],
                        "title": company_data[name_idx],
                        "exchange": company_data[exchange_idx]
                        if exchange_idx < len(company_data)
                        else None,
                    }
                    results.append(company_dict)

        return results
