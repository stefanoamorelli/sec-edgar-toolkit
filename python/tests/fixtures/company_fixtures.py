"""Company-related test fixtures."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from sec_edgar_toolkit.types import CompanySubmissions


@pytest.fixture
def mock_company_tickers() -> Dict[str, Any]:
    """Mock company tickers response data (matches real SEC API format)."""
    return {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
            [1559720, "Alphabet Inc.", "GOOGL", "Nasdaq"],
        ]
    }


@pytest.fixture
def mock_company_submissions() -> CompanySubmissions:
    """Mock company submissions response data."""
    return {
        "cik": "0000320193",
        "entityType": "operating",
        "sic": "3571",
        "sicDescription": "Electronic Computers",
        "insiderTransactionForOwnerExists": True,
        "insiderTransactionForIssuerExists": True,
        "name": "Apple Inc.",
        "tickers": ["AAPL"],
        "exchanges": ["Nasdaq"],
        "ein": "942404110",
        "description": "Large accelerated filer",
        "website": "http://www.apple.com",
        "investorWebsite": "http://investor.apple.com",
        "category": "Large accelerated filer",
        "fiscalYearEnd": "0930",
        "stateOfIncorporation": "CA",
        "stateOfIncorporationDescription": "California",
        "addresses": {
            "mailing": {
                "street1": "One Apple Park Way",
                "street2": None,
                "city": "Cupertino",
                "stateOrCountry": "CA",
                "zipCode": "95014",
                "stateOrCountryDescription": "CA",
            },
            "business": {
                "street1": "One Apple Park Way",
                "street2": None,
                "city": "Cupertino",
                "stateOrCountry": "CA",
                "zipCode": "95014",
                "stateOrCountryDescription": "CA",
            },
        },
        "phone": "14089961010",
        "flags": "",
        "formerNames": [
            {"name": "APPLE COMPUTER INC", "from": "1997-07-08", "to": "2007-01-04"}
        ],
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000320193-23-000077",
                    "0000320193-23-000064",
                    "0000320193-23-000052",
                ],
                "filingDate": ["2023-08-04", "2023-05-04", "2023-02-03"],
                "reportDate": ["2023-07-01", "2023-04-01", "2022-12-31"],
                "acceptanceDateTime": [
                    "2023-08-04T16:31:27.000Z",
                    "2023-05-04T16:31:49.000Z",
                    "2023-02-03T16:35:25.000Z",
                ],
                "act": ["34", "34", "34"],
                "form": ["10-Q", "10-Q", "10-K"],
                "fileNumber": ["001-36743", "001-36743", "001-36743"],
                "filmNumber": ["231215242", "23893195", "23588466"],
                "items": ["", "", ""],
                "size": [4904320, 4826946, 42935364],
                "isXBRL": [True, True, True],
                "isInlineXBRL": [True, True, True],
                "primaryDocument": ["aapl-20230701.htm", "aapl-20230401.htm", "aapl-20221231.htm"],
                "primaryDocDescription": [
                    "10-Q",
                    "10-Q",
                    "10-K",
                ],
            },
            "files": [],
        },
    }


# Export fixtures for easy access
company_fixtures = {
    "mock_company_tickers": mock_company_tickers,
    "mock_company_submissions": mock_company_submissions,
}
