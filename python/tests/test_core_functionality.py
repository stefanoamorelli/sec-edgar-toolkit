"""Tests for core edgartools-compatible functionality."""

import pytest
from unittest.mock import Mock, patch

from sec_edgar_toolkit.core import (
    Company,
    Filing,
    XBRLInstance,
    find_company,
    get_filings,
    search,
    set_identity,
)
from sec_edgar_toolkit.client import SecEdgarApi


class TestGlobalFunctions:
    """Test global functions."""

    def test_set_identity(self):
        """Test set_identity function."""
        user_agent = "TestApp/1.0 (test@example.com)"
        set_identity(user_agent)
        
        # Should not raise an error
        assert True

    @patch('sec_edgar_toolkit.core.global_functions._get_api')
    def test_find_company_by_ticker(self, mock_get_api):
        """Test find_company with ticker."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_by_ticker.return_value = {
            "cik_str": "0000320193",
            "ticker": "AAPL", 
            "title": "Apple Inc."
        }
        mock_get_api.return_value = mock_api
        
        company = find_company("AAPL")
        
        assert company is not None
        assert company.ticker == "AAPL"
        assert company.cik == "0000320193"
        mock_api.get_company_by_ticker.assert_called_once_with("AAPL")

    @patch('sec_edgar_toolkit.core.global_functions._get_api')
    def test_find_company_by_cik(self, mock_get_api):
        """Test find_company with CIK."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_by_ticker.return_value = None
        mock_api.get_company_by_cik.return_value = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
        mock_get_api.return_value = mock_api
        
        company = find_company("0000320193")
        
        assert company is not None
        assert company.cik == "0000320193"
        mock_api.get_company_by_cik.assert_called_once_with("0000320193")

    @patch('sec_edgar_toolkit.core.global_functions._get_api')
    def test_search_companies(self, mock_get_api):
        """Test search function."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.search_companies.return_value = [
            {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."},
            {"cik_str": "0001018724", "ticker": "AMZN", "title": "Amazon.com Inc."}
        ]
        mock_get_api.return_value = mock_api
        
        companies = search("tech")
        
        assert len(companies) == 2
        assert all(isinstance(c, Company) for c in companies)
        mock_api.search_companies.assert_called_once_with("tech")

    @patch('sec_edgar_toolkit.core.global_functions._get_api')
    def test_get_filings_with_ticker(self, mock_get_api):
        """Test get_filings with ticker filter."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_by_ticker.return_value = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
        mock_api.get_company_submissions.return_value = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-23-000077", "0000320193-23-000064"],
                    "form": ["10-K", "10-Q"],
                    "filingDate": ["2023-11-03", "2023-08-04"]
                }
            }
        }
        mock_get_api.return_value = mock_api
        
        filings = get_filings(ticker="AAPL", form="10-K", limit=1)
        
        assert len(filings) == 1
        assert isinstance(filings[0], Filing)
        assert filings[0].form_type == "10-K"


class TestCompany:
    """Test Company class."""

    def test_company_init_with_data(self):
        """Test Company initialization with pre-loaded data."""
        mock_api = Mock(spec=SecEdgarApi)
        company_data = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc.",
            "exchange": "NASDAQ"
        }
        
        company = Company("AAPL", api=mock_api, _company_data=company_data)
        
        assert company.cik == "0000320193"
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
        assert company.exchange == "NASDAQ"

    def test_company_str_repr(self):
        """Test Company string representations."""
        mock_api = Mock(spec=SecEdgarApi)
        company_data = {
            "cik_str": "0000320193",
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
        
        company = Company("AAPL", api=mock_api, _company_data=company_data)
        
        assert str(company) == "AAPL: Apple Inc."
        assert "Company(cik='0000320193'" in repr(company)

    def test_get_filings(self):
        """Test Company.get_filings method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_submissions.return_value = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-23-000077"],
                    "form": ["10-K"],
                    "filingDate": ["2023-11-03"]
                }
            }
        }
        company_data = {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."}
        
        company = Company("AAPL", api=mock_api, _company_data=company_data)
        filings = company.get_filings(form="10-K")
        
        assert len(filings) == 1
        assert isinstance(filings[0], Filing)
        mock_api.get_company_submissions.assert_called_once()

    def test_get_company_facts(self):
        """Test Company.get_company_facts method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {"units": {"USD": [{"val": 1000000}]}}
                }
            }
        }
        company_data = {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."}
        
        company = Company("AAPL", api=mock_api, _company_data=company_data)
        facts = company.get_company_facts()
        
        assert "facts" in facts
        assert "us-gaap" in facts["facts"]
        mock_api.get_company_facts.assert_called_once_with("0000320193")


class TestFiling:
    """Test Filing class."""

    def test_filing_init(self):
        """Test Filing initialization."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        assert filing.cik == "0000320193"
        assert filing.accession_number == "0000320193-23-000077"
        assert filing.form_type == "10-K"
        assert filing.filing_date == "2023-11-03"

    def test_filing_url_construction(self):
        """Test Filing URL construction."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        expected_url = "https://www.sec.gov/Archives/edgar/data/0000320193/000032019323000077/0000320193-23-000077-index.htm"
        assert filing.url == expected_url

    def test_filing_str_repr(self):
        """Test Filing string representations."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077", 
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        assert "10-K filing for CIK 0000320193" in str(filing)
        assert "Filing(cik='0000320193'" in repr(filing)

    @patch.object(Filing, '_fetch_filing_content')
    def test_text_method(self, mock_fetch):
        """Test Filing.text method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_fetch.return_value = "<html><body>Test content</body></html>"
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K", 
            filing_date="2023-11-03",
            api=mock_api
        )
        
        # Test text format (cleaned)
        text = filing.text(format="text")
        assert "Test content" in text
        assert "<html>" not in text
        
        # Test raw format
        raw = filing.text(format="raw")
        assert "<html>" in raw

    def test_xbrl_method(self):
        """Test Filing.xbrl method."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = filing.xbrl()
        assert isinstance(xbrl, XBRLInstance)
        assert xbrl.filing == filing


class TestXBRLInstance:
    """Test XBRLInstance class."""

    def test_xbrl_init(self):
        """Test XBRLInstance initialization."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        
        assert xbrl.filing == filing
        assert xbrl.cik == "0000320193"

    def test_facts_property(self):
        """Test XBRLInstance.facts property."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {"Assets": {"units": {"USD": [{"val": 1000000}]}}},
                "dei": {"EntityCentralIndexKey": {"units": {"pure": [{"val": "0000320193"}]}}}
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        facts = xbrl.facts
        
        assert "facts" in facts
        assert "us-gaap" in facts["facts"]
        mock_api.get_company_facts.assert_called_once_with("0000320193")

    def test_us_gaap_property(self):
        """Test XBRLInstance.us_gaap property."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {"Assets": {"units": {"USD": [{"val": 1000000}]}}}
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        us_gaap = xbrl.us_gaap
        
        assert "Assets" in us_gaap

    def test_query_method(self):
        """Test XBRLInstance.query method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                {"val": 1000000, "fy": 2023, "fp": "FY", "filed": "2023-11-03"}
                            ]
                        }
                    }
                }
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        results = xbrl.query(concept="Assets", unit="USD")
        
        assert len(results) == 1
        assert results[0]["concept"] == "Assets"
        assert results[0]["value"] == 1000000

    def test_find_statement_method(self):
        """Test XBRLInstance.find_statement method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [{"val": 1000000, "fy": 2023, "filed": "2023-11-03"}]
                        }
                    }
                }
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        statement = xbrl.find_statement("balance_sheet")
        
        assert statement is not None
        assert statement["statement_type"] == "balance_sheet"
        assert "data" in statement

    def test_get_concept_value(self):
        """Test XBRLInstance.get_concept_value method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [{"val": 1000000, "fy": 2023, "filed": "2023-11-03"}]
                        }
                    }
                }
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        value = xbrl.get_concept_value("Assets")
        
        assert value == 1000000

    def test_list_concepts(self):
        """Test XBRLInstance.list_concepts method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {"units": {"USD": []}},
                    "Liabilities": {"units": {"USD": []}}
                }
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        concepts = xbrl.list_concepts("us-gaap")
        
        assert "Assets" in concepts
        assert "Liabilities" in concepts

    def test_to_dict_method(self):
        """Test XBRLInstance.to_dict method."""
        mock_api = Mock(spec=SecEdgarApi)
        mock_api.get_company_facts.return_value = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [{"val": 1000000, "fy": 2023, "filed": "2023-11-03"}]
                        }
                    }
                }
            }
        }
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        data = xbrl.to_dict(concept="Assets")
        
        assert "metadata" in data
        assert "facts" in data
        assert data["metadata"]["cik"] == "0000320193"
        assert len(data["facts"]) == 1

    def test_xbrl_str_repr(self):
        """Test XBRLInstance string representations."""
        mock_api = Mock(spec=SecEdgarApi)
        
        filing = Filing(
            cik="0000320193",
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date="2023-11-03",
            api=mock_api
        )
        
        xbrl = XBRLInstance(filing, api=mock_api)
        
        assert "XBRL instance for 10-K filing" in str(xbrl)
        assert "XBRLInstance(cik='0000320193'" in repr(xbrl)