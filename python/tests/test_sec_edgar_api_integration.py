"""
Integration tests for SEC EDGAR API client.

This module contains integration tests that simulate real-world usage scenarios
with mocked responses for reproducibility and reliability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pytest
import responses

from sec_edgar_toolkit import NotFoundError, SecEdgarApi


class TestSecEdgarApiIntegration:
    """Integration test suite for SEC EDGAR API client."""

    @pytest.fixture
    def api_client(self) -> SecEdgarApi:
        """Create a test API client instance."""
        return SecEdgarApi(
            user_agent="IntegrationTest/1.0 (test@example.com)",
            rate_limit_delay=0.01,  # Faster for tests
        )

    @pytest.fixture
    def mock_full_response_data(self) -> Dict[str, Any]:
        """Create comprehensive mock data for integration tests."""
        return {
            "company_tickers": {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [
                    [320193, "Apple Inc.", "AAPL", "Nasdaq"],
                    [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
                    [1018724, "AMAZON COM INC", "AMZN", "Nasdaq"],
                    [1326801, "Meta Platforms, Inc.", "META", "Nasdaq"],
                    [1559720, "Alphabet Inc.", "GOOGL", "Nasdaq"],
                ]
            },
            "apple_submissions": {
                "cik": "0000320193",
                "entityType": "operating",
                "sic": "3571",
                "sicDescription": "Electronic Computers",
                "name": "Apple Inc.",
                "tickers": ["AAPL"],
                "exchanges": ["Nasdaq"],
                "ein": "942404110",
                "website": "http://www.apple.com",
                "filings": {
                    "recent": {
                        "accessionNumber": [
                            "0000320193-23-000106",
                            "0000320193-23-000077",
                            "0000320193-23-000064",
                            "0000320193-23-000052",
                            "0000320193-22-000108",
                        ],
                        "filingDate": [
                            "2023-11-03",
                            "2023-08-04",
                            "2023-05-04",
                            "2023-02-03",
                            "2022-11-04",
                        ],
                        "reportDate": [
                            "2023-09-30",
                            "2023-07-01",
                            "2023-04-01",
                            "2022-12-31",
                            "2022-09-24",
                        ],
                        "form": ["10-K", "10-Q", "10-Q", "10-Q", "10-K"],
                        "primaryDocument": [
                            "aapl-20230930.htm",
                            "aapl-20230701.htm",
                            "aapl-20230401.htm",
                            "aapl-20221231.htm",
                            "aapl-20220924.htm",
                        ],
                        "size": [45000000, 4904320, 4826946, 4735821, 42935364],
                        "isXBRL": [True, True, True, True, True],
                        "isInlineXBRL": [True, True, True, True, True],
                    }
                },
            },
            "apple_facts": {
                "cik": "0000320193",
                "entityName": "Apple Inc.",
                "facts": {
                    "us-gaap": {
                        "Assets": {
                            "label": "Assets",
                            "description": "Total assets",
                            "units": {
                                "USD": [
                                    {
                                        "fy": 2023,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2023-11-03",
                                        "val": 352755000000,
                                    },
                                    {
                                        "fy": 2022,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2022-11-04",
                                        "val": 352755000000,
                                    },
                                ]
                            },
                        },
                        "NetIncomeLoss": {
                            "label": "Net Income (Loss)",
                            "description": "Net income or loss",
                            "units": {
                                "USD": [
                                    {
                                        "fy": 2023,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2023-11-03",
                                        "val": 96995000000,
                                    },
                                    {
                                        "fy": 2022,
                                        "fp": "FY",
                                        "form": "10-K",
                                        "filed": "2022-11-04",
                                        "val": 99803000000,
                                    },
                                ]
                            },
                        },
                    }
                },
            },
        }

    @responses.activate
    def test_complete_workflow_company_lookup_and_filings(
        self,
        api_client: SecEdgarApi,
        mock_full_response_data: Dict[str, Any],
    ) -> None:
        """Test complete workflow: lookup company, get filings, get facts."""
        # Mock company tickers endpoint
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_full_response_data["company_tickers"],
            status=200,
        )

        # Step 1: Search for Apple by ticker
        company = api_client.get_company_by_ticker("AAPL")
        assert company is not None
        assert company["cik_str"] == "0000320193"
        assert company["title"] == "Apple Inc."

        # Mock submissions endpoint
        cik = company["cik_str"]
        responses.add(
            responses.GET,
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            json=mock_full_response_data["apple_submissions"],
            status=200,
        )

        # Step 2: Get company submissions
        submissions = api_client.get_company_submissions(cik)
        assert submissions["name"] == "Apple Inc."
        assert len(submissions["filings"]["recent"]["form"]) == 5

        # Step 3: Filter for 10-K filings
        annual_reports = api_client.get_company_submissions(cik, submission_type="10-K")
        forms = annual_reports["filings"]["recent"]["form"]
        assert all(form == "10-K" for form in forms)
        assert len(forms) == 2

        # Mock facts endpoint
        responses.add(
            responses.GET,
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            json=mock_full_response_data["apple_facts"],
            status=200,
        )

        # Step 4: Get financial facts
        facts = api_client.get_company_facts(cik)
        assert "us-gaap" in facts["facts"]
        assert "Assets" in facts["facts"]["us-gaap"]

        # Check assets values
        assets_data = facts["facts"]["us-gaap"]["Assets"]["units"]["USD"]
        assert len(assets_data) == 2
        assert assets_data[0]["val"] == 352755000000

    @responses.activate
    def test_multi_company_analysis(
        self,
        api_client: SecEdgarApi,
        mock_full_response_data: Dict[str, Any],
    ) -> None:
        """Test analyzing multiple companies."""
        # Mock company tickers
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_full_response_data["company_tickers"],
            status=200,
        )

        # Search for tech companies
        tech_companies = ["AAPL", "MSFT", "GOOGL", "META", "AMZN"]
        found_companies = []

        for ticker in tech_companies:
            company = api_client.get_company_by_ticker(ticker)
            if company:
                found_companies.append(company)

        assert len(found_companies) == 5
        assert all(c["ticker"] in tech_companies for c in found_companies)

        # Verify all are on Nasdaq
        assert all(c["exchange"] == "Nasdaq" for c in found_companies)

    @responses.activate
    def test_company_search_variations(
        self,
        api_client: SecEdgarApi,
        mock_full_response_data: Dict[str, Any],
    ) -> None:
        """Test various company search methods."""
        # Mock company tickers
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_full_response_data["company_tickers"],
            status=200,
        )

        # Search by partial name
        results = api_client.search_companies("Inc.")
        assert len(results) == 3  # Apple Inc., AMAZON COM INC, Alphabet Inc.

        # Search case variations
        apple1 = api_client.get_company_by_ticker("AAPL")
        apple2 = api_client.get_company_by_ticker("aapl")
        apple3 = api_client.get_company_by_ticker("AaPl")
        assert apple1 is not None
        assert apple2 is not None
        assert apple3 is not None
        assert apple1 == apple2 == apple3

        # Search by CIK variations
        apple_by_cik1 = api_client.get_company_by_cik("0000320193")
        apple_by_cik2 = api_client.get_company_by_cik("320193")
        apple_by_cik3 = api_client.get_company_by_cik(320193)
        assert apple_by_cik1 is not None
        assert apple_by_cik2 is not None
        assert apple_by_cik3 is not None
        assert apple_by_cik1 == apple_by_cik2 == apple_by_cik3
        assert apple_by_cik1["ticker"] == "AAPL"

    @responses.activate
    def test_date_filtered_submissions(
        self,
        api_client: SecEdgarApi,
        mock_full_response_data: Dict[str, Any],
    ) -> None:
        """Test filtering submissions by date ranges."""
        cik = "0000320193"

        responses.add(
            responses.GET,
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            json=mock_full_response_data["apple_submissions"],
            status=200,
        )

        # Get filings from 2023 only
        filings_2023 = api_client.get_company_submissions(
            cik,
            from_date="2023-01-01",
            to_date="2023-12-31",
        )

        dates = filings_2023["filings"]["recent"]["filingDate"]
        assert all(date.startswith("2023") for date in dates)
        assert len(dates) == 4  # 4 filings in 2023

        # Get Q3 2023 filings
        q3_filings = api_client.get_company_submissions(
            cik,
            from_date="2023-07-01",
            to_date="2023-09-30",
        )

        dates = q3_filings["filings"]["recent"]["filingDate"]
        assert len(dates) == 1
        assert dates[0] == "2023-08-04"

    @responses.activate
    def test_xbrl_concept_data_retrieval(
        self,
        api_client: SecEdgarApi,
    ) -> None:
        """Test retrieving specific XBRL concept data."""
        cik = "0000320193"
        taxonomy = "us-gaap"
        tag = "NetIncomeLoss"

        mock_concept = {
            "cik": cik,
            "taxonomy": taxonomy,
            "tag": tag,
            "label": "Net Income (Loss)",
            "entityName": "Apple Inc.",
            "units": {
                "USD": [
                    {
                        "fy": 2023,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2023-11-03",
                        "val": 96995000000,
                    },
                    {
                        "fy": 2023,
                        "fp": "Q3",
                        "form": "10-Q",
                        "filed": "2023-08-04",
                        "val": 19881000000,
                    },
                    {
                        "fy": 2023,
                        "fp": "Q2",
                        "form": "10-Q",
                        "filed": "2023-05-04",
                        "val": 19881000000,
                    },
                ]
            },
        }

        responses.add(
            responses.GET,
            f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json",
            json=mock_concept,
            status=200,
        )

        # Get net income data
        result = api_client.get_company_concept(cik, taxonomy, tag, unit="USD")

        usd_data = result["units"]["USD"]
        assert len(usd_data) == 3

        # Check annual vs quarterly data
        annual_data = [d for d in usd_data if d["fp"] == "FY"]
        quarterly_data = [d for d in usd_data if d["fp"].startswith("Q")]

        assert len(annual_data) == 1
        assert len(quarterly_data) == 2
        assert annual_data[0]["val"] == 96995000000

    @responses.activate
    def test_frame_data_aggregation(
        self,
        api_client: SecEdgarApi,
    ) -> None:
        """Test retrieving aggregated frame data across companies."""
        taxonomy = "us-gaap"
        tag = "Assets"
        unit = "USD"
        year = 2023
        quarter = 4

        mock_frame = {
            "taxonomy": taxonomy,
            "tag": tag,
            "ccp": f"CY{year}Q{quarter}",
            "uom": unit,
            "label": "Assets",
            "pts": 3245,  # Number of data points
            "data": [
                {
                    "accn": "0000320193-23-000106",
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
                {
                    "accn": "0001018724-23-000004",
                    "cik": "0001018724",
                    "entityName": "AMAZON COM INC",
                    "loc": "US-WA",
                    "end": "2023-09-30",
                    "val": 527854000000,
                },
            ],
        }

        responses.add(
            responses.GET,
            f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{year}Q{quarter}.json",
            json=mock_frame,
            status=200,
        )

        # Get assets data for all companies
        result = api_client.get_frames(taxonomy, tag, unit, year, quarter)

        assert result["pts"] == 3245
        assert len(result["data"]) == 3

        # Analyze top companies by assets
        companies_by_assets = sorted(
            result["data"],
            key=lambda x: x["val"],
            reverse=True,
        )

        assert companies_by_assets[0]["entityName"] == "AMAZON COM INC"
        assert companies_by_assets[0]["val"] == 527854000000
        assert companies_by_assets[1]["entityName"] == "MICROSOFT CORP"
        assert companies_by_assets[2]["entityName"] == "Apple Inc."

    @responses.activate
    def test_filing_document_retrieval(
        self,
        api_client: SecEdgarApi,
    ) -> None:
        """Test retrieving specific filing documents."""
        cik = "0000320193"
        accession_number = "0000320193-23-000077"

        mock_filing = {
            "accessionNumber": accession_number,
            "filingDate": "2023-08-04",
            "acceptanceDateTime": "2023-08-04T16:31:27.000Z",
            "reportDate": "2023-07-01",
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
                },
                {
                    "sequence": "2",
                    "filename": "exhibit31-1.htm",
                    "description": "EX-31.1",
                    "type": "EX-31.1",
                    "size": "12853",
                },
                {
                    "sequence": "3",
                    "filename": "exhibit31-2.htm",
                    "description": "EX-31.2",
                    "type": "EX-31.2",
                    "size": "12847",
                },
                {
                    "sequence": "4",
                    "filename": "exhibit32-1.htm",
                    "description": "EX-32.1",
                    "type": "EX-32.1",
                    "size": "9398",
                },
            ],
        }

        accession_clean = accession_number.replace("-", "")
        url = (
            f"https://data.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession_clean}/{accession_number}-index.json"
        )

        responses.add(
            responses.GET,
            url,
            json=mock_filing,
            status=200,
        )

        # Get filing details
        result = api_client.get_filing(cik, accession_number)

        assert result["form"] == "10-Q"
        assert result["filingDate"] == "2023-08-04"
        assert len(result["documents"]) == 4

        # Check primary document
        primary_doc = result["documents"][0]
        assert primary_doc["filename"] == "aapl-20230701.htm"
        assert primary_doc["type"] == "10-Q"

        # Check exhibits
        exhibits = [d for d in result["documents"] if d["type"].startswith("EX-")]
        assert len(exhibits) == 3

    @responses.activate
    def test_error_scenarios(
        self,
        api_client: SecEdgarApi,
    ) -> None:
        """Test various error scenarios."""
        # Test 404 for non-existent CIK
        bad_cik = "9999999999"
        responses.add(
            responses.GET,
            f"https://data.sec.gov/submissions/CIK{bad_cik}.json",
            status=404,
        )

        with pytest.raises(NotFoundError):
            api_client.get_company_submissions(bad_cik)

        # Test rate limiting with multiple rapid requests
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json={"data": []},
            status=200,
        )

        # Make multiple requests quickly
        start_time = datetime.now()
        for _ in range(3):
            api_client.get_company_tickers(force_refresh=True)

        elapsed = (datetime.now() - start_time).total_seconds()
        # Should have rate limited (3 requests * 0.01s delay)
        assert elapsed >= 0.02

    @responses.activate
    def test_caching_behavior(
        self,
        api_client: SecEdgarApi,
        mock_full_response_data: Dict[str, Any],
    ) -> None:
        """Test caching behavior for company tickers."""
        responses.add(
            responses.GET,
            api_client.company.COMPANY_TICKERS_URL,
            json=mock_full_response_data["company_tickers"],
            status=200,
        )

        # First call - hits API
        result1 = api_client.get_company_tickers()
        assert len(responses.calls) == 1

        # Multiple subsequent calls - use cache
        for _ in range(5):
            result = api_client.get_company_tickers()
            assert result == result1

        # Still only one API call
        assert len(responses.calls) == 1

        # Force refresh
        api_client.get_company_tickers(force_refresh=True)
        assert len(responses.calls) == 2

