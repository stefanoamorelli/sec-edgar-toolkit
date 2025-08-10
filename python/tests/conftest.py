"""Pytest configuration and shared fixtures."""

import pytest

from sec_edgar_toolkit.client import SecEdgarApi

# Import all fixtures
from .fixtures.company_fixtures import mock_company_tickers, mock_company_submissions
from .fixtures.filing_fixtures import mock_filing_data, mock_xbrl_facts, mock_frame_data


@pytest.fixture
def api_client() -> SecEdgarApi:
    """Create a test API client instance."""
    return SecEdgarApi(user_agent="TestClient/1.0 (test@example.com)")
