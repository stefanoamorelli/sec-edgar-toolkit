"""
Unit tests for SEC EDGAR API client.

This module contains comprehensive unit tests for the SecEdgarApi class,
including tests for all endpoints, error handling, rate limiting, and caching.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import patch

import pytest
import responses
from requests.exceptions import Timeout

from sec_edgar_toolkit import (
    AuthenticationError,
    CompanySubmissions,
    CompanyTicker,
    NotFoundError,
    RateLimitError,
    SecEdgarApi,
    SecEdgarApiError,
)


class TestSecEdgarApi:
    """Test suite for SEC EDGAR API client."""

    def test_init_valid_user_agent(self) -> None:
        """Test initialization with valid user agent."""
        api = SecEdgarApi("MyApp/1.0 (contact@example.com)")
        assert api.user_agent == "MyApp/1.0 (contact@example.com)"
        assert api.rate_limit_delay == 0.1
        assert api.timeout == 30

    def test_init_invalid_user_agent(self) -> None:
        """Test initialization with invalid user agent."""
        with pytest.raises(ValueError, match="User-Agent is required"):
            SecEdgarApi("")

        with pytest.raises(ValueError, match="User-Agent is required"):
            SecEdgarApi("short")

    def test_init_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        api = SecEdgarApi(
            user_agent="TestApp/2.0 (test@test.com)",
            rate_limit_delay=0.5,
            max_retries=5,
            timeout=60,
        )
        assert api.rate_limit_delay == 0.5
        assert api.timeout == 60

    @responses.activate
    def test_get_company_tickers_success(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test successful retrieval of company tickers."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        result = api_client.get_company_tickers()
        assert result == mock_company_tickers
        assert len(result["data"]) == 3
        assert result["data"][0][2] == "AAPL"  # ticker is at index 2

    @responses.activate
    def test_get_company_tickers_caching(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test that company tickers are cached."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        # First call should hit the API
        result1 = api_client.get_company_tickers()
        assert len(responses.calls) == 1

        # Second call should use cache
        result2 = api_client.get_company_tickers()
        assert len(responses.calls) == 1  # No additional call
        assert result1 == result2

        # Force refresh should hit the API again
        result3 = api_client.get_company_tickers(force_refresh=True)
        assert len(responses.calls) == 2
        assert result1 == result3

    @responses.activate
    def test_get_company_by_ticker_found(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test finding company by ticker."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        company = api_client.get_company_by_ticker("AAPL")
        assert company is not None
        assert company["ticker"] == "AAPL"
        assert company["cik_str"] == "0000320193"
        assert company["title"] == "Apple Inc."

    @responses.activate
    def test_get_company_by_ticker_not_found(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test company not found by ticker."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        company = api_client.get_company_by_ticker("INVALID")
        assert company is None

    @responses.activate
    def test_get_company_by_ticker_case_insensitive(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test ticker search is case insensitive."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        company = api_client.get_company_by_ticker("aapl")
        assert company is not None
        assert company["ticker"] == "AAPL"

    @responses.activate
    def test_get_company_by_cik_found(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test finding company by CIK."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        # Test with full CIK
        company = api_client.get_company_by_cik("0000320193")
        assert company is not None
        assert company["cik_str"] == "0000320193"
        assert company["ticker"] == "AAPL"

        # Test with numeric CIK
        company = api_client.get_company_by_cik(320193)
        assert company is not None
        assert company["cik_str"] == "0000320193"

    @responses.activate
    def test_get_company_by_cik_not_found(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test company not found by CIK."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        company = api_client.get_company_by_cik("9999999999")
        assert company is None

    @responses.activate
    def test_search_companies(
        self, api_client: SecEdgarApi, mock_company_tickers: Dict[str, Any]
    ) -> None:
        """Test searching companies by name."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_company_tickers,
            status=200,
        )

        # Search for "Inc"
        results = api_client.search_companies("Inc")
        assert len(results) == 2  # Apple Inc. and Alphabet Inc.
        assert all("Inc." in company["title"] for company in results)

        # Search case insensitive
        results = api_client.search_companies("apple")
        assert len(results) == 1
        assert results[0]["ticker"] == "AAPL"

        # Search with no results
        results = api_client.search_companies("Tesla")
        assert len(results) == 0

    @responses.activate
    def test_get_company_submissions_success(
        self, api_client: SecEdgarApi, mock_company_submissions: CompanySubmissions
    ) -> None:
        """Test successful retrieval of company submissions."""
        cik = "0000320193"
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        responses.add(
            responses.GET,
            url,
            json=mock_company_submissions,
            status=200,
        )

        result = api_client.get_company_submissions(cik)
        assert result["cik"] == cik
        assert result["name"] == "Apple Inc."
        assert len(result["filings"]["recent"]["form"]) == 3

    @responses.activate
    def test_get_company_submissions_with_filters(
        self, api_client: SecEdgarApi, mock_company_submissions: CompanySubmissions
    ) -> None:
        """Test company submissions with filters."""
        cik = "0000320193"
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        responses.add(
            responses.GET,
            url,
            json=mock_company_submissions,
            status=200,
        )

        # Filter by form type
        result = api_client.get_company_submissions(cik, submission_type="10-K")
        forms = result["filings"]["recent"]["form"]
        assert len(forms) == 1
        assert forms[0] == "10-K"

        # Filter by date range
        result = api_client.get_company_submissions(
            cik,
            from_date="2023-05-01",
            to_date="2023-12-31",
        )
        dates = result["filings"]["recent"]["filingDate"]
        assert len(dates) == 2
        assert all(date >= "2023-05-01" for date in dates)

    @responses.activate
    def test_get_company_facts_success(self, api_client: SecEdgarApi) -> None:
        """Test successful retrieval of company facts."""
        cik = "0000789019"
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

        mock_facts = {
            "cik": cik,
            "entityName": "MICROSOFT CORP",
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Assets",
                        "description": "Total assets",
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "val": 411976000000},
                                {"fy": 2022, "fp": "FY", "val": 364840000000},
                            ]
                        },
                    }
                }
            },
        }

        responses.add(
            responses.GET,
            url,
            json=mock_facts,
            status=200,
        )

        result = api_client.get_company_facts(cik)
        assert result["cik"] == cik
        assert "us-gaap" in result["facts"]
        assert "Assets" in result["facts"]["us-gaap"]

    @responses.activate
    def test_get_company_concept_success(self, api_client: SecEdgarApi) -> None:
        """Test successful retrieval of company concept data."""
        cik = "0000320193"
        taxonomy = "us-gaap"
        tag = "Assets"
        url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"

        mock_concept = {
            "cik": cik,
            "taxonomy": taxonomy,
            "tag": tag,
            "label": "Assets",
            "description": "Total assets",
            "entityName": "Apple Inc.",
            "units": {
                "USD": [
                    {
                        "fy": 2023,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2023-11-03",
                        "val": 352755000000,
                    }
                ],
                "EUR": [
                    {
                        "fy": 2023,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2023-11-03",
                        "val": 320000000000,
                    }
                ],
            },
        }

        responses.add(
            responses.GET,
            url,
            json=mock_concept,
            status=200,
        )

        # Get all units
        result = api_client.get_company_concept(cik, taxonomy, tag)
        assert result["cik"] == cik
        assert len(result["units"]) == 2

        # Filter by unit
        result = api_client.get_company_concept(cik, taxonomy, tag, unit="USD")
        assert len(result["units"]) == 1
        assert "USD" in result["units"]
        assert "EUR" not in result["units"]

    @responses.activate
    def test_get_frames_success(self, api_client: SecEdgarApi) -> None:
        """Test successful retrieval of frame data."""
        taxonomy = "us-gaap"
        tag = "Assets"
        unit = "USD"
        year = 2023
        quarter = 4

        url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{year}Q{quarter}.json"

        mock_frame = {
            "taxonomy": taxonomy,
            "tag": tag,
            "ccp": f"CY{year}Q{quarter}",
            "uom": unit,
            "label": "Assets",
            "description": "Total assets",
            "pts": 12345,
            "data": [
                {
                    "accn": "0000320193-23-000077",
                    "cik": "0000320193",
                    "entityName": "Apple Inc.",
                    "loc": "US-CA",
                    "end": "2023-09-30",
                    "val": 352755000000,
                },
                {
                    "accn": "0000789019-23-000013",
                    "cik": "0000789019",
                    "entityName": "MICROSOFT CORP",
                    "loc": "US-WA",
                    "end": "2023-09-30",
                    "val": 411976000000,
                },
            ],
        }

        responses.add(
            responses.GET,
            url,
            json=mock_frame,
            status=200,
        )

        result = api_client.get_frames(taxonomy, tag, unit, year, quarter)
        assert result["taxonomy"] == taxonomy
        assert result["tag"] == tag
        assert len(result["data"]) == 2

    @responses.activate
    def test_get_frames_annual(self, api_client: SecEdgarApi) -> None:
        """Test frame data for annual period."""
        taxonomy = "us-gaap"
        tag = "Revenues"
        unit = "USD"
        year = 2023

        url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{year}.json"

        responses.add(
            responses.GET,
            url,
            json={"data": []},
            status=200,
        )

        api_client.get_frames(taxonomy, tag, unit, year)
        assert responses.calls[-1].request.url is not None
        assert responses.calls[-1].request.url.endswith(f"CY{year}.json")

    @responses.activate
    def test_get_frames_instantaneous(self, api_client: SecEdgarApi) -> None:
        """Test frame data for instantaneous period."""
        taxonomy = "us-gaap"
        tag = "Assets"
        unit = "USD"
        year = 2023
        quarter = 4

        url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{year}Q{quarter}I.json"

        responses.add(
            responses.GET,
            url,
            json={"data": []},
            status=200,
        )

        api_client.get_frames(taxonomy, tag, unit, year, quarter, instantaneous=True)
        assert responses.calls[-1].request.url is not None
        assert responses.calls[-1].request.url.endswith(f"CY{year}Q{quarter}I.json")

    @responses.activate
    def test_get_filing_success(self, api_client: SecEdgarApi) -> None:
        """Test successful retrieval of filing details."""
        cik = "0000320193"
        accession_number = "0000320193-23-000077"
        accession_clean = accession_number.replace("-", "")

        url = (
            f"https://data.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession_clean}/{accession_number}-index.json"
        )

        mock_filing = {
            "accessionNumber": accession_number,
            "filingDate": "2023-08-04",
            "acceptanceDateTime": "2023-08-04T16:31:27.000Z",
            "form": "10-Q",
            "primaryDocument": "aapl-20230701.htm",
            "items": "2.02,9.01",
            "documents": [
                {
                    "sequence": "1",
                    "filename": "aapl-20230701.htm",
                    "description": "10-Q",
                    "type": "10-Q",
                    "size": "2904320",
                }
            ],
        }

        responses.add(
            responses.GET,
            url,
            json=mock_filing,
            status=200,
        )

        result = api_client.get_filing(cik, accession_number)
        assert result["accessionNumber"] == accession_number
        assert result["form"] == "10-Q"
        assert len(result["documents"]) == 1

    def test_rate_limiting(self, api_client: SecEdgarApi) -> None:
        """Test rate limiting functionality."""
        api_client.http_client.rate_limit_delay = 0.1

        with patch.object(api_client.http_client.session, 'get') as mock_get:
            mock_get.return_value.json.return_value = {"data": []}
            mock_get.return_value.status_code = 200

            start = time.time()
            api_client.http_client.get("http://test.com/1")
            api_client.http_client.get("http://test.com/2")
            elapsed = time.time() - start

            # Should have waited at least rate_limit_delay between requests
            assert elapsed >= api_client.http_client.rate_limit_delay

    def test_error_handling_rate_limit(self, api_client: SecEdgarApi) -> None:
        """Test handling of rate limit errors."""
        # Override the session to remove 429 from retry status codes
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=0,  # No retries
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],  # Don't retry on 429
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        api_client.http_client.session.mount("http://", adapter)
        api_client.http_client.session.mount("https://", adapter)

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "http://test.com/api",
                status=429,
            )

            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                api_client.http_client.get("http://test.com/api")

    @responses.activate
    def test_error_handling_authentication(self, api_client: SecEdgarApi) -> None:
        """Test handling of authentication errors."""
        responses.add(
            responses.GET,
            "http://test.com/api",
            status=401,
        )

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            api_client.http_client.get("http://test.com/api")

    @responses.activate
    def test_error_handling_not_found(self, api_client: SecEdgarApi) -> None:
        """Test handling of 404 errors."""
        responses.add(
            responses.GET,
            "http://test.com/api",
            status=404,
        )

        with pytest.raises(NotFoundError, match="Resource not found"):
            api_client.http_client.get("http://test.com/api")

    @responses.activate
    def test_error_handling_server_error(self, api_client: SecEdgarApi) -> None:
        """Test handling of server errors."""
        responses.add(
            responses.GET,
            "http://test.com/api",
            status=500,
        )

        with pytest.raises(SecEdgarApiError, match="API request failed"):
            api_client.http_client.get("http://test.com/api")

    @responses.activate
    def test_error_handling_timeout(self, api_client: SecEdgarApi) -> None:
        """Test handling of timeout errors."""
        def timeout_callback(request):
            raise Timeout("Request timed out")

        responses.add_callback(
            responses.GET,
            "http://test.com/api",
            callback=timeout_callback,
        )

        with pytest.raises(SecEdgarApiError, match="API request failed"):
            api_client.http_client.get("http://test.com/api")

    def test_session_headers(self, api_client: SecEdgarApi) -> None:
        """Test that session headers are properly set."""
        assert api_client.http_client.session.headers["User-Agent"] == api_client.http_client.user_agent
        assert api_client.http_client.session.headers["Accept"] == "application/json"
        assert "gzip" in api_client.http_client.session.headers["Accept-Encoding"]

    def test_filter_filings_empty(self, api_client: SecEdgarApi) -> None:
        """Test filtering with empty filings."""
        from sec_edgar_toolkit.utils.filters import FilingFilter

        result = FilingFilter.filter_filings({}, None, None, None)
        assert result == {}

        result = FilingFilter.filter_filings({"accessionNumber": []}, "10-K", None, None)
        assert result == {"accessionNumber": []}

    def test_filter_filings_by_form_type(self, api_client: SecEdgarApi) -> None:
        """Test filtering filings by form type."""
        from sec_edgar_toolkit.utils.filters import FilingFilter

        filings = {
            "accessionNumber": ["001", "002", "003"],
            "form": ["10-K", "10-Q", "10-K"],
            "filingDate": ["2023-01-01", "2023-04-01", "2023-12-31"],
        }

        result = FilingFilter.filter_filings(filings, "10-K", None, None)
        assert len(result["accessionNumber"]) == 2
        assert result["accessionNumber"] == ["001", "003"]
        assert result["form"] == ["10-K", "10-K"]

    def test_filter_filings_by_date_range(self, api_client: SecEdgarApi) -> None:
        """Test filtering filings by date range."""
        from sec_edgar_toolkit.utils.filters import FilingFilter

        filings = {
            "accessionNumber": ["001", "002", "003"],
            "form": ["10-K", "10-Q", "8-K"],
            "filingDate": ["2023-01-01", "2023-06-15", "2023-12-31"],
        }

        result = FilingFilter.filter_filings(
            filings,
            None,
            "2023-06-01",
            "2023-12-01",
        )
        assert len(result["accessionNumber"]) == 1
        assert result["accessionNumber"] == ["002"]

    def test_filter_filings_combined_filters(self, api_client: SecEdgarApi) -> None:
        """Test filtering with multiple criteria."""
        from sec_edgar_toolkit.utils.filters import FilingFilter

        filings = {
            "accessionNumber": ["001", "002", "003", "004"],
            "form": ["10-K", "10-Q", "10-K", "10-Q"],
            "filingDate": ["2023-01-01", "2023-04-01", "2023-07-01", "2023-10-01"],
        }

        result = FilingFilter.filter_filings(
            filings,
            "10-Q",
            "2023-03-01",
            "2023-09-01",
        )
        assert len(result["accessionNumber"]) == 1
        assert result["accessionNumber"] == ["002"]
        assert result["form"] == ["10-Q"]


class TestTypeDefinitions:
    """Test type definitions and TypedDict structures."""

    def test_company_ticker_type(self) -> None:
        """Test CompanyTicker type definition."""
        ticker: CompanyTicker = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc.",
            "exchange": "Nasdaq",
        }
        assert ticker["cik_str"] == "0000320193"
        assert ticker["exchange"] == "Nasdaq"

    def test_company_ticker_optional_exchange(self) -> None:
        """Test CompanyTicker with optional exchange."""
        ticker: CompanyTicker = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc.",
            "exchange": None,
        }
        assert ticker["exchange"] is None

