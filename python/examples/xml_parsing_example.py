#!/usr/bin/env python3
"""
XML Parsing Example for SEC EDGAR Toolkit.

This script demonstrates how to parse SEC ownership forms (Form 3, 4, and 5) 
from XML documents using the SEC EDGAR Toolkit parsers.

Forms covered:
- Form 3: Initial statement of beneficial ownership
- Form 4: Changes in beneficial ownership (insider transactions)
- Form 5: Annual statement of changes in beneficial ownership
"""

import os
from datetime import datetime
from pathlib import Path

from sec_edgar_toolkit.parsers import Form4Parser, Form5Parser, OwnershipFormParser
from sec_edgar_toolkit.parsers.ownership_forms import OwnershipFormParseError


def format_currency(amount: float) -> str:
    """Format a number as currency."""
    if amount == 0:
        return "$0.00"
    return f"${amount:,.2f}"


def format_shares(shares: float) -> str:
    """Format share count."""
    if shares == int(shares):
        return f"{int(shares):,}"
    return f"{shares:,.2f}"


def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_document_info(doc_info: dict) -> None:
    """Print document information."""
    print_section_header("DOCUMENT INFORMATION")
    print(f"Form Type: {doc_info.get('form_type', 'N/A')}")
    print(f"Schema Version: {doc_info.get('schema_version', 'N/A')}")
    
    period = doc_info.get('period_of_report')
    if period:
        print(f"Reporting Period: {period.strftime('%B %d, %Y')}")
    
    submission_date = doc_info.get('date_of_original_submission')
    if submission_date:
        print(f"Submission Date: {submission_date.strftime('%B %d, %Y')}")
    
    not_subject = doc_info.get('not_subject_to_section16')
    if not_subject is not None:
        print(f"Subject to Section 16: {'No' if not_subject else 'Yes'}")


def print_issuer_info(issuer_info: dict) -> None:
    """Print issuer (company) information."""
    print_section_header("ISSUER INFORMATION")
    print(f"Company: {issuer_info.get('name', 'N/A')}")
    print(f"Trading Symbol: {issuer_info.get('trading_symbol', 'N/A')}")
    print(f"CIK: {issuer_info.get('cik', 'N/A')}")


def print_reporting_owner_info(owner_info: dict) -> None:
    """Print reporting owner (insider) information."""
    print_section_header("REPORTING OWNER INFORMATION")
    print(f"Name: {owner_info.get('name', 'N/A')}")
    print(f"CIK: {owner_info.get('cik', 'N/A')}")
    
    # Address information
    address_parts = []
    if owner_info.get('street1'):
        address_parts.append(owner_info['street1'])
    if owner_info.get('street2'):
        address_parts.append(owner_info['street2'])
    if owner_info.get('city'):
        city_state_zip = owner_info['city']
        if owner_info.get('state'):
            city_state_zip += f", {owner_info['state']}"
        if owner_info.get('zip_code'):
            city_state_zip += f" {owner_info['zip_code']}"
        address_parts.append(city_state_zip)
    
    if address_parts:
        print(f"Address: {' | '.join(address_parts)}")
    
    # Relationship information
    relationship = owner_info.get('relationship', {})
    roles = []
    if relationship.get('is_director'):
        roles.append("Director")
    if relationship.get('is_officer'):
        roles.append("Officer")
    if relationship.get('is_ten_percent_owner'):
        roles.append("10% Owner")
    if relationship.get('is_other'):
        roles.append("Other")
    
    if roles:
        print(f"Roles: {', '.join(roles)}")
    
    if relationship.get('officer_title'):
        print(f"Officer Title: {relationship['officer_title']}")
    
    if relationship.get('other_text'):
        print(f"Other Description: {relationship['other_text']}")


def print_non_derivative_transactions(transactions: list) -> None:
    """Print non-derivative transactions."""
    if not transactions:
        return
    
    print_section_header("NON-DERIVATIVE TRANSACTIONS")
    
    for i, transaction in enumerate(transactions, 1):
        print(f"\nTransaction #{i}:")
        print(f"  Security: {transaction.get('security_title', 'N/A')}")
        
        trans_date = transaction.get('transaction_date')
        if trans_date:
            print(f"  Date: {trans_date.strftime('%B %d, %Y')}")
        
        print(f"  Transaction Code: {transaction.get('code', 'N/A')}")
        
        shares = transaction.get('shares', 0)
        price = transaction.get('price_per_share', 0)
        acquired_disposed = transaction.get('acquired_disposed_code', 'N/A')
        
        print(f"  Shares: {format_shares(shares)}")
        print(f"  Price per Share: {format_currency(price)}")
        print(f"  Total Value: {format_currency(shares * price)}")
        print(f"  Acquired/Disposed: {'Acquired' if acquired_disposed == 'A' else 'Disposed' if acquired_disposed == 'D' else acquired_disposed}")
        
        shares_owned = transaction.get('shares_owned_following_transaction', 0)
        print(f"  Shares Owned After Transaction: {format_shares(shares_owned)}")
        
        ownership_type = transaction.get('direct_or_indirect_ownership', 'N/A')
        print(f"  Ownership Type: {'Direct' if ownership_type == 'D' else 'Indirect' if ownership_type == 'I' else ownership_type}")
        
        nature = transaction.get('nature_of_ownership')
        if nature:
            print(f"  Nature of Ownership: {nature}")


def print_non_derivative_holdings(holdings: list) -> None:
    """Print non-derivative holdings."""
    if not holdings:
        return
    
    print_section_header("NON-DERIVATIVE HOLDINGS")
    
    for i, holding in enumerate(holdings, 1):
        print(f"\nHolding #{i}:")
        print(f"  Security: {holding.get('security_title', 'N/A')}")
        
        shares = holding.get('shares_owned', 0)
        print(f"  Shares Owned: {format_shares(shares)}")
        
        ownership_type = holding.get('direct_or_indirect_ownership', 'N/A')
        print(f"  Ownership Type: {'Direct' if ownership_type == 'D' else 'Indirect' if ownership_type == 'I' else ownership_type}")
        
        nature = holding.get('nature_of_ownership')
        if nature:
            print(f"  Nature of Ownership: {nature}")


def print_derivative_transactions(transactions: list) -> None:
    """Print derivative transactions."""
    if not transactions:
        return
    
    print_section_header("DERIVATIVE TRANSACTIONS")
    
    for i, transaction in enumerate(transactions, 1):
        print(f"\nDerivative Transaction #{i}:")
        print(f"  Security: {transaction.get('security_title', 'N/A')}")
        
        exercise_price = transaction.get('conversion_or_exercise_price', 0)
        print(f"  Exercise/Conversion Price: {format_currency(exercise_price)}")
        
        trans_date = transaction.get('transaction_date')
        if trans_date:
            print(f"  Transaction Date: {trans_date.strftime('%B %d, %Y')}")
        
        shares = transaction.get('shares', 0)
        total_value = transaction.get('total_value', 0)
        print(f"  Shares: {format_shares(shares)}")
        print(f"  Total Value: {format_currency(total_value)}")
        
        exercise_date = transaction.get('exercise_date')
        if exercise_date:
            print(f"  Exercise Date: {exercise_date.strftime('%B %d, %Y')}")
        
        expiration_date = transaction.get('expiration_date')
        if expiration_date:
            print(f"  Expiration Date: {expiration_date.strftime('%B %d, %Y')}")
        
        underlying = transaction.get('underlying_security', {})
        if underlying:
            print(f"  Underlying Security: {underlying.get('title', 'N/A')}")
            underlying_shares = underlying.get('shares', 0)
            print(f"  Underlying Shares: {format_shares(underlying_shares)}")


def parse_sample_form4() -> None:
    """Parse and display the sample Form 4."""
    print("🔍 Parsing Sample Form 4 (Apple Inc. - Tim Cook)")
    
    # Get the path to the sample XML file
    current_dir = Path(__file__).parent
    test_fixtures_dir = current_dir.parent / "tests" / "fixtures"
    form4_path = test_fixtures_dir / "form4_sample.xml"
    
    if not form4_path.exists():
        print(f"❌ Sample Form 4 file not found at {form4_path}")
        return
    
    try:
        # Read and parse the XML file
        with open(form4_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        parser = Form4Parser(xml_content)
        data = parser.parse_all()
        
        # Display all sections
        print_document_info(data['document_info'])
        print_issuer_info(data['issuer_info'])
        print_reporting_owner_info(data['reporting_owner_info'])
        print_non_derivative_transactions(data['non_derivative_transactions'])
        print_non_derivative_holdings(data['non_derivative_holdings'])
        print_derivative_transactions(data['derivative_transactions'])
        
        print(f"\n✅ Successfully parsed Form 4!")
        
    except OwnershipFormParseError as e:
        print(f"❌ Parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def parse_sample_form5() -> None:
    """Parse and display the sample Form 5."""
    print("\n" + "="*80)
    print("🔍 Parsing Sample Form 5 (Microsoft Corp. - Satya Nadella)")
    
    # Get the path to the sample XML file
    current_dir = Path(__file__).parent
    test_fixtures_dir = current_dir.parent / "tests" / "fixtures"
    form5_path = test_fixtures_dir / "form5_sample.xml"
    
    if not form5_path.exists():
        print(f"❌ Sample Form 5 file not found at {form5_path}")
        return
    
    try:
        # Read and parse the XML file
        with open(form5_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        parser = Form5Parser(xml_content)
        data = parser.parse_all()
        
        # Display all sections
        print_document_info(data['document_info'])
        print_issuer_info(data['issuer_info'])
        print_reporting_owner_info(data['reporting_owner_info'])
        print_non_derivative_transactions(data['non_derivative_transactions'])
        print_non_derivative_holdings(data['non_derivative_holdings'])
        print_derivative_transactions(data['derivative_transactions'])
        
        print(f"\n✅ Successfully parsed Form 5!")
        
    except OwnershipFormParseError as e:
        print(f"❌ Parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def demonstrate_error_handling() -> None:
    """Demonstrate error handling with invalid XML."""
    print("\n" + "="*80)
    print("🔍 Demonstrating Error Handling")
    
    invalid_xml = "<invalid>unclosed tag"
    
    try:
        parser = OwnershipFormParser(invalid_xml)
        print("❌ This should not happen - invalid XML was accepted")
    except OwnershipFormParseError as e:
        print(f"✅ Successfully caught parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error type: {e}")


def parse_custom_xml_file(file_path: str) -> None:
    """Parse a custom XML file provided by the user."""
    print(f"\n🔍 Parsing custom XML file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Try to determine form type and use appropriate parser
        parser = OwnershipFormParser(xml_content)
        
        if parser.form_type == "4":
            parser = Form4Parser(xml_content)
            print("📄 Detected Form 4 - using specialized parser")
        elif parser.form_type == "5":
            parser = Form5Parser(xml_content)
            print("📄 Detected Form 5 - using specialized parser")
        else:
            print(f"📄 Detected Form {parser.form_type} - using general parser")
        
        data = parser.parse_all()
        
        # Display all sections
        print_document_info(data['document_info'])
        print_issuer_info(data['issuer_info'])
        print_reporting_owner_info(data['reporting_owner_info'])
        print_non_derivative_transactions(data['non_derivative_transactions'])
        print_non_derivative_holdings(data['non_derivative_holdings'])
        print_derivative_transactions(data['derivative_transactions'])
        
        print(f"\n✅ Successfully parsed {file_path}!")
        
    except OwnershipFormParseError as e:
        print(f"❌ Parsing error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Main function demonstrating XML parsing capabilities."""
    print("📋 SEC EDGAR Toolkit - XML Parsing Examples")
    print("=" * 80)
    print("This example demonstrates parsing SEC ownership forms (Forms 3, 4, and 5)")
    print("from XML documents. These forms contain insider transaction data.")
    print()
    
    # Parse sample forms
    parse_sample_form4()
    parse_sample_form5()
    
    # Demonstrate error handling
    demonstrate_error_handling()
    
    # Check if user provided a custom XML file as command line argument
    import sys
    if len(sys.argv) > 1:
        custom_file = sys.argv[1]
        parse_custom_xml_file(custom_file)
    else:
        print("\n" + "="*80)
        print("💡 Pro Tip:")
        print("You can parse your own XML files by running:")
        print("python xml_parsing_example.py /path/to/your/form.xml")
    
    print("\n" + "="*80)
    print("🎉 XML Parsing examples completed!")
    print()
    print("Key capabilities demonstrated:")
    print("• Parsing Form 4 (insider transactions)")
    print("• Parsing Form 5 (annual ownership statements)")
    print("• Extracting issuer information (company details)")
    print("• Extracting reporting owner information (insider details)")
    print("• Parsing transaction data (buys, sells, option exercises)")
    print("• Parsing holdings data (current ownership positions)")
    print("• Error handling for malformed XML")
    print("• Date parsing in multiple formats")
    print("• Currency and share formatting")


if __name__ == "__main__":
    main()