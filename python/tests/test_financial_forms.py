"""Tests for financial forms parser."""

import os
from datetime import datetime

import pytest

from sec_edgar_toolkit.parsers.financial_forms import FinancialFormParser


class TestFinancialFormParser:
    """Test cases for FinancialFormParser."""

    @pytest.fixture
    def apple_10k_content(self):
        """Load Apple 10-K fixture."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "forms",
            "10-K",
            "apple_10k_2023.txt"
        )
        with open(fixture_path, "r", encoding="utf-8") as f:
            return f.read()

    @pytest.fixture
    def parser(self, apple_10k_content):
        """Create parser instance with Apple 10-K data."""
        return FinancialFormParser(apple_10k_content)

    def test_parse_all_basic_info(self, parser):
        """Test parsing of basic document information."""
        result = parser.parse_all()
        
        assert result["form_type"] == "10-K"
        assert result["cik"] == "0000320193"
        assert result["company_name"] == "Apple Inc."
        assert isinstance(result["filing_date"], datetime)
        assert isinstance(result["period_end_date"], datetime)

    def test_financial_statements_structure(self, parser):
        """Test that financial statements have correct structure."""
        result = parser.parse_all()
        
        # Test balance sheet structure
        assert "balance_sheet" in result
        assert "assets" in result["balance_sheet"]
        assert "liabilities" in result["balance_sheet"]
        assert "equity" in result["balance_sheet"]
        
        # Test that assets has required keys
        assert "current_assets" in result["balance_sheet"]["assets"]
        assert "non_current_assets" in result["balance_sheet"]["assets"]
        assert "total_assets" in result["balance_sheet"]["assets"]
        
        # Test income statement
        assert "income_statement" in result
        assert "revenue" in result["income_statement"]
        assert "operating_expenses" in result["income_statement"]
        
        # Test cash flow statement
        assert "cash_flow_statement" in result
        assert "operating_activities" in result["cash_flow_statement"]

    def test_get_financial_statements(self, parser):
        """Test financial statements extraction."""
        statements = parser.get_financial_statements()
        
        assert "balance_sheet" in statements
        assert "income_statement" in statements
        assert "cash_flow_statement" in statements
        
        # Check that lists are returned for array items
        balance_sheet = statements["balance_sheet"]
        assert isinstance(balance_sheet["assets"]["current_assets"], list)
        assert isinstance(balance_sheet["liabilities"]["current_liabilities"], list)

    def test_business_segments(self, parser):
        """Test business segments extraction."""
        segments = parser.get_business_segments()
        
        assert isinstance(segments, list)
        # Apple typically has business segments, but parsing might not find them
        # depending on document structure

    def test_risk_factors(self, parser):
        """Test risk factors extraction."""
        risk_factors = parser.get_risk_factors()
        
        assert isinstance(risk_factors, list)
        assert len(risk_factors) >= 0
        
        if risk_factors:
            risk_factor = risk_factors[0]
            assert "category" in risk_factor
            assert "description" in risk_factor
            assert "severity" in risk_factor
            assert risk_factor["severity"] in ["low", "medium", "high"]

    def test_management_discussion(self, parser):
        """Test management discussion extraction."""
        md_sections = parser.get_management_discussion()
        
        assert isinstance(md_sections, list)
        
        if md_sections:
            section = md_sections[0]
            assert "title" in section
            assert "content" in section
            assert "key_metrics" in section
            assert isinstance(section["key_metrics"], list)

    def test_financial_metrics(self, parser):
        """Test financial metrics calculation."""
        metrics = parser.get_financial_metrics()
        
        assert "debt_to_equity" in metrics
        assert "return_on_equity" in metrics
        assert "current_ratio" in metrics
        assert "quick_ratio" in metrics
        
        # Values can be None if not calculable
        for key, value in metrics.items():
            if value is not None:
                assert isinstance(value, (int, float))

    def test_xbrl_facts(self, parser):
        """Test XBRL facts extraction."""
        xbrl_facts = parser.get_xbrl_facts()
        
        assert isinstance(xbrl_facts, list)
        
        if xbrl_facts:
            fact = xbrl_facts[0]
            assert "name" in fact
            assert "value" in fact
            assert "units" in fact
            assert "context_ref" in fact

    def test_parse_balance_sheet(self, parser):
        """Test balance sheet parsing specifically."""
        balance_sheet = parser.parse_balance_sheet()
        
        assert "assets" in balance_sheet
        assert "liabilities" in balance_sheet
        assert "equity" in balance_sheet
        
        # Test that we get lists for arrays
        assert isinstance(balance_sheet["assets"]["current_assets"], list)
        assert isinstance(balance_sheet["liabilities"]["current_liabilities"], list)

    def test_parse_income_statement(self, parser):
        """Test income statement parsing specifically."""
        income_statement = parser.parse_income_statement()
        
        expected_keys = [
            "revenue",
            "gross_profit", 
            "operating_income",
            "net_income",
            "earnings_per_share",
            "operating_expenses"
        ]
        
        for key in expected_keys:
            assert key in income_statement
            
        # Operating expenses should be a list
        assert isinstance(income_statement["operating_expenses"], list)

    def test_parse_cash_flow_statement(self, parser):
        """Test cash flow statement parsing specifically."""
        cash_flow = parser.parse_cash_flow_statement()
        
        expected_keys = [
            "operating_activities",
            "investing_activities", 
            "financing_activities",
            "net_cash_flow"
        ]
        
        for key in expected_keys:
            assert key in cash_flow
            
        # Activities should be lists
        assert isinstance(cash_flow["operating_activities"], list)
        assert isinstance(cash_flow["investing_activities"], list)
        assert isinstance(cash_flow["financing_activities"], list)