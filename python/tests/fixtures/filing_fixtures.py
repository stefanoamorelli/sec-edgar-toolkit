"""Filing-related test fixtures."""

from __future__ import annotations

from typing import Any, Dict

import pytest


@pytest.fixture
def mock_filing_data() -> Dict[str, Any]:
    """Mock filing response data."""
    return {
        "accessionNumber": "0000320193-23-000077",
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
        ],
    }


@pytest.fixture
def mock_xbrl_facts() -> Dict[str, Any]:
    """Mock XBRL facts response data."""
    return {
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
    }


@pytest.fixture
def mock_frame_data() -> Dict[str, Any]:
    """Mock frame response data."""
    return {
        "taxonomy": "us-gaap",
        "tag": "Assets",
        "ccp": "CY2023Q4",
        "uom": "USD",
        "label": "Assets",
        "description": "Total assets",
        "pts": 3245,
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
        ],
    }


# Export fixtures for easy access
filing_fixtures = {
    "mock_filing_data": mock_filing_data,
    "mock_xbrl_facts": mock_xbrl_facts,
    "mock_frame_data": mock_frame_data,
}
