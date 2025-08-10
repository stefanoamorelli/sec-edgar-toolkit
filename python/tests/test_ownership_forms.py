"""
Tests for SEC ownership forms (Form 3, 4, and 5) XML parsing.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from sec_edgar_toolkit.parsers import Form4Parser, Form5Parser, OwnershipFormParser
from sec_edgar_toolkit.parsers.ownership_forms import OwnershipFormParseError


# Get the directory containing this test file
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"


@pytest.fixture
def form4_xml():
    """Load Form 4 sample XML data."""
    with open(FIXTURES_DIR / "form4_sample.xml", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def form5_xml():
    """Load Form 5 sample XML data."""
    with open(FIXTURES_DIR / "form5_sample.xml", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def invalid_xml():
    """Invalid XML for testing error handling."""
    return "<invalid>unclosed tag"


class TestOwnershipFormParser:
    """Test the base OwnershipFormParser class."""

    def test_init_with_valid_xml(self, form4_xml):
        """Test parser initialization with valid XML."""
        parser = OwnershipFormParser(form4_xml)
        assert parser.form_type == "4"
        assert parser.xml_content == form4_xml
        assert parser.root is not None

    def test_init_with_bytes(self, form4_xml):
        """Test parser initialization with bytes input."""
        xml_bytes = form4_xml.encode('utf-8')
        parser = OwnershipFormParser(xml_bytes)
        assert parser.form_type == "4"

    def test_init_with_invalid_xml(self, invalid_xml):
        """Test parser initialization with invalid XML raises exception."""
        with pytest.raises(OwnershipFormParseError):
            OwnershipFormParser(invalid_xml)

    def test_extract_form_type(self, form4_xml, form5_xml):
        """Test form type extraction."""
        parser4 = OwnershipFormParser(form4_xml)
        assert parser4.form_type == "4"
        
        parser5 = OwnershipFormParser(form5_xml)
        assert parser5.form_type == "5"

    def test_parse_document_info(self, form4_xml):
        """Test document information parsing."""
        parser = OwnershipFormParser(form4_xml)
        doc_info = parser.parse_document_info()
        
        assert doc_info['form_type'] == "4"
        assert doc_info['schema_version'] == "X0306"
        assert doc_info['document_type'] == "4"
        assert doc_info['period_of_report'] == datetime(2024, 1, 15)
        assert doc_info['not_subject_to_section16'] is False

    def test_parse_issuer_info(self, form4_xml):
        """Test issuer information parsing."""
        parser = OwnershipFormParser(form4_xml)
        issuer_info = parser.parse_issuer_info()
        
        assert issuer_info['cik'] == "0000320193"
        assert issuer_info['name'] == "Apple Inc."
        assert issuer_info['trading_symbol'] == "AAPL"

    def test_parse_reporting_owner_info(self, form4_xml):
        """Test reporting owner information parsing."""
        parser = OwnershipFormParser(form4_xml)
        owner_info = parser.parse_reporting_owner_info()
        
        assert owner_info['cik'] == "0001214128"
        assert owner_info['name'] == "COOK TIMOTHY D"
        assert owner_info['street1'] == "ONE APPLE PARK WAY"
        assert owner_info['city'] == "CUPERTINO"
        assert owner_info['state'] == "CA"
        assert owner_info['zip_code'] == "95014"
        
        relationship = owner_info['relationship']
        assert relationship['is_director'] is True
        assert relationship['is_officer'] is True
        assert relationship['is_ten_percent_owner'] is False
        assert relationship['is_other'] is False
        assert relationship['officer_title'] == "Chief Executive Officer"

    def test_parse_non_derivative_transactions(self, form4_xml):
        """Test non-derivative transaction parsing."""
        parser = OwnershipFormParser(form4_xml)
        transactions = parser.parse_non_derivative_transactions()
        
        assert len(transactions) == 1
        transaction = transactions[0]
        
        assert transaction['security_title'] == "Common Stock"
        assert transaction['transaction_date'] == datetime(2024, 1, 15)
        assert transaction['shares'] == 1000.0
        assert transaction['price_per_share'] == 185.50
        assert transaction['acquired_disposed_code'] == "D"
        assert transaction['form_type'] == "4"
        assert transaction['code'] == "S"
        assert transaction['equity_swap_involved'] is False
        assert transaction['shares_owned_following_transaction'] == 3425000.0
        assert transaction['direct_or_indirect_ownership'] == "D"
        assert transaction['nature_of_ownership'] == "Direct"

    def test_parse_non_derivative_holdings(self, form4_xml):
        """Test non-derivative holdings parsing."""
        parser = OwnershipFormParser(form4_xml)
        holdings = parser.parse_non_derivative_holdings()
        
        assert len(holdings) == 1
        holding = holdings[0]
        
        assert holding['security_title'] == "Common Stock"
        assert holding['shares_owned'] == 3425000.0
        assert holding['direct_or_indirect_ownership'] == "D"
        assert holding['nature_of_ownership'] == "Direct"

    def test_parse_derivative_transactions(self, form4_xml):
        """Test derivative transaction parsing."""
        parser = OwnershipFormParser(form4_xml)
        transactions = parser.parse_derivative_transactions()
        
        assert len(transactions) == 1
        transaction = transactions[0]
        
        assert transaction['security_title'] == "Employee Stock Option"
        assert transaction['conversion_or_exercise_price'] == 125.0
        assert transaction['transaction_date'] == datetime(2024, 1, 15)
        assert transaction['shares'] == 500.0
        assert transaction['total_value'] == 62500.0
        assert transaction['acquired_disposed_code'] == "A"
        assert transaction['exercise_date'] == datetime(2020, 1, 15)
        assert transaction['expiration_date'] == datetime(2030, 1, 15)
        
        underlying = transaction['underlying_security']
        assert underlying['title'] == "Common Stock"
        assert underlying['shares'] == 500.0

    def test_parse_all(self, form4_xml):
        """Test parsing all information from the form."""
        parser = OwnershipFormParser(form4_xml)
        data = parser.parse_all()
        
        assert 'document_info' in data
        assert 'issuer_info' in data
        assert 'reporting_owner_info' in data
        assert 'non_derivative_transactions' in data
        assert 'non_derivative_holdings' in data
        assert 'derivative_transactions' in data
        
        # Verify some key data is present
        assert data['document_info']['form_type'] == "4"
        assert data['issuer_info']['name'] == "Apple Inc."
        assert data['reporting_owner_info']['name'] == "COOK TIMOTHY D"
        assert len(data['non_derivative_transactions']) == 1
        assert len(data['non_derivative_holdings']) == 1
        assert len(data['derivative_transactions']) == 1

    def test_date_parsing_multiple_formats(self):
        """Test parsing dates in different formats."""
        parser = OwnershipFormParser("<test><documentType>4</documentType></test>")
        
        # Test different date formats
        test_dates = [
            ("2024-01-15", datetime(2024, 1, 15)),
            ("01/15/2024", datetime(2024, 1, 15)),
            ("01-15-2024", datetime(2024, 1, 15)),
        ]
        
        for date_str, expected in test_dates:
            from xml.etree import ElementTree as ET
            elem = ET.Element("date")
            elem.text = date_str
            result = parser._get_date(elem)
            assert result == expected

    def test_date_parsing_invalid_format(self):
        """Test parsing invalid date formats returns None."""
        parser = OwnershipFormParser("<test><documentType>4</documentType></test>")
        
        from xml.etree import ElementTree as ET
        elem = ET.Element("date")
        elem.text = "invalid-date"
        result = parser._get_date(elem)
        assert result is None

    def test_get_text_with_none_element(self):
        """Test _get_text method with None element."""
        parser = OwnershipFormParser("<test><documentType>4</documentType></test>")
        result = parser._get_text(None, "default")
        assert result == "default"

    def test_get_float_with_invalid_text(self):
        """Test _get_float method with invalid text."""
        parser = OwnershipFormParser("<test><documentType>4</documentType></test>")
        
        from xml.etree import ElementTree as ET
        elem = ET.Element("number")
        elem.text = "not-a-number"
        result = parser._get_float(elem, 99.0)
        assert result == 99.0


class TestForm4Parser:
    """Test the Form4Parser specialized class."""

    def test_init_with_form4(self, form4_xml):
        """Test Form4Parser initialization with Form 4 XML."""
        parser = Form4Parser(form4_xml)
        assert parser.form_type == "4"

    def test_init_with_wrong_form_type(self, form5_xml):
        """Test Form4Parser with Form 5 XML (should log warning but work)."""
        parser = Form4Parser(form5_xml)
        assert parser.form_type == "5"  # Still works, just logs warning


class TestForm5Parser:
    """Test the Form5Parser specialized class."""

    def test_init_with_form5(self, form5_xml):
        """Test Form5Parser initialization with Form 5 XML."""
        parser = Form5Parser(form5_xml)
        assert parser.form_type == "5"

    def test_form5_specific_data(self, form5_xml):
        """Test parsing Form 5 specific data."""
        parser = Form5Parser(form5_xml)
        data = parser.parse_all()
        
        # Check issuer info for Microsoft
        assert data['issuer_info']['name'] == "Microsoft Corporation"
        assert data['issuer_info']['trading_symbol'] == "MSFT"
        assert data['issuer_info']['cik'] == "0000789019"
        
        # Check reporting owner info for Satya Nadella
        assert data['reporting_owner_info']['name'] == "NADELLA SATYA"
        assert data['reporting_owner_info']['relationship']['officer_title'] == "Chairman and Chief Executive Officer"

    def test_init_with_wrong_form_type(self, form4_xml):
        """Test Form5Parser with Form 4 XML (should log warning but work)."""
        parser = Form5Parser(form4_xml)
        assert parser.form_type == "4"  # Still works, just logs warning


class TestIntegration:
    """Integration tests for the ownership form parsers."""

    def test_form4_complete_parsing(self, form4_xml):
        """Test complete Form 4 parsing workflow."""
        parser = Form4Parser(form4_xml)
        
        # Parse all data
        data = parser.parse_all()
        
        # Verify document structure
        assert data['document_info']['form_type'] == "4"
        assert data['document_info']['period_of_report'] == datetime(2024, 1, 15)
        
        # Verify issuer (Apple)
        assert data['issuer_info']['name'] == "Apple Inc."
        assert data['issuer_info']['trading_symbol'] == "AAPL"
        
        # Verify reporting owner (Tim Cook)
        assert data['reporting_owner_info']['name'] == "COOK TIMOTHY D"
        assert data['reporting_owner_info']['relationship']['officer_title'] == "Chief Executive Officer"
        
        # Verify transactions
        assert len(data['non_derivative_transactions']) == 1
        transaction = data['non_derivative_transactions'][0]
        assert transaction['code'] == "S"  # Sale
        assert transaction['shares'] == 1000.0
        assert transaction['price_per_share'] == 185.50
        
        # Verify derivative transactions (stock options)
        assert len(data['derivative_transactions']) == 1
        derivative = data['derivative_transactions'][0]
        assert derivative['security_title'] == "Employee Stock Option"
        assert derivative['conversion_or_exercise_price'] == 125.0

    def test_form5_complete_parsing(self, form5_xml):
        """Test complete Form 5 parsing workflow."""
        parser = Form5Parser(form5_xml)
        
        # Parse all data
        data = parser.parse_all()
        
        # Verify document structure
        assert data['document_info']['form_type'] == "5"
        assert data['document_info']['period_of_report'] == datetime(2023, 12, 31)
        
        # Verify issuer (Microsoft)
        assert data['issuer_info']['name'] == "Microsoft Corporation"
        assert data['issuer_info']['trading_symbol'] == "MSFT"
        
        # Verify reporting owner (Satya Nadella)
        assert data['reporting_owner_info']['name'] == "NADELLA SATYA"
        assert data['reporting_owner_info']['relationship']['officer_title'] == "Chairman and Chief Executive Officer"
        
        # Verify transactions
        assert len(data['non_derivative_transactions']) == 1
        transaction = data['non_derivative_transactions'][0]
        assert transaction['code'] == "A"  # Acquired
        assert transaction['shares'] == 2500.0
        assert transaction['price_per_share'] == 0.0  # Likely stock grant

    @pytest.mark.parametrize("parser_class,xml_fixture", [
        (Form4Parser, "form4_xml"),
        (Form5Parser, "form5_xml"),
    ])
    def test_parser_types(self, parser_class, xml_fixture, request):
        """Test different parser types with their respective XML data."""
        xml_data = request.getfixturevalue(xml_fixture)
        parser = parser_class(xml_data)
        
        # Should parse without errors
        data = parser.parse_all()
        
        # Should have all required sections
        required_sections = [
            'document_info',
            'issuer_info', 
            'reporting_owner_info',
            'non_derivative_transactions',
            'non_derivative_holdings',
            'derivative_transactions'
        ]
        
        for section in required_sections:
            assert section in data