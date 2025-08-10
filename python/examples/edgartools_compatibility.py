"""
Example demonstrating edgartools-compatible API usage.

This example shows how to use the SEC EDGAR Toolkit with the same
interface that edgartools provides, making it a drop-in replacement.
"""

import os
from sec_edgar_toolkit import (
    Company,
    Filing,
    find_company,
    get_filings,
    search,
    set_identity,
)


def main():
    """Demonstrate edgartools-compatible usage."""
    
    # Set user identity (required by SEC)
    user_agent = os.getenv("SEC_EDGAR_TOOLKIT_USER_AGENT", "Example/1.0 (test@example.com)")
    set_identity(user_agent)
    print(f"Set identity: {user_agent}")
    
    # 1. Find a company by ticker
    print("\n1. Finding company by ticker...")
    company = find_company("AAPL")
    if company:
        print(f"Found: {company}")
        print(f"  CIK: {company.cik}")
        print(f"  Name: {company.name}")
        print(f"  Ticker: {company.ticker}")
    else:
        print("Company not found")
        return
    
    # 2. Search for companies
    print("\n2. Searching for companies...")
    companies = search("Apple")
    print(f"Found {len(companies)} companies matching 'Apple':")
    for i, comp in enumerate(companies[:3]):  # Show first 3
        print(f"  {i+1}. {comp}")
    
    # 3. Get company filings
    print("\n3. Getting company filings...")
    filings = company.get_filings(form="10-K", limit=2)
    print(f"Found {len(filings)} recent 10-K filings:")
    for filing in filings:
        print(f"  - {filing}")
    
    if not filings:
        print("No filings found")
        return
    
    # 4. Work with a specific filing
    print("\n4. Working with a filing...")
    filing = filings[0]
    print(f"Selected filing: {filing}")
    
    # Get filing text content (first 500 characters)
    try:
        text_content = filing.text()
        print(f"Text content preview: {text_content[:500]}...")
    except Exception as e:
        print(f"Could not fetch text content: {e}")
    
    # Get structured data
    try:
        obj_data = filing.obj()
        print(f"Structured data keys: {list(obj_data.keys())}")
    except Exception as e:
        print(f"Could not parse structured data: {e}")
    
    # 5. Work with XBRL data
    print("\n5. Working with XBRL data...")
    try:
        xbrl = filing.xbrl()
        print(f"XBRL instance: {xbrl}")
        
        # Query specific concepts
        assets = xbrl.query(concept="Assets", unit="USD")
        if assets:
            print(f"Found {len(assets)} Assets entries")
            latest = assets[-1]  # Most recent
            print(f"  Latest Assets value: ${latest.get('value', 0):,.0f}")
        
        # Get a specific value
        total_assets = xbrl.get_concept_value("Assets")
        if total_assets:
            print(f"Total Assets: ${total_assets:,.0f}")
        
        # List available concepts
        concepts = xbrl.list_concepts("us-gaap")
        print(f"Available US-GAAP concepts: {len(concepts)}")
        print(f"Sample concepts: {concepts[:5]}")
        
    except Exception as e:
        print(f"Could not work with XBRL data: {e}")
    
    # 6. Get filings globally (across companies)
    print("\n6. Getting filings globally...")
    try:
        global_filings = get_filings(form="8-K", limit=3)
        print(f"Found {len(global_filings)} recent 8-K filings across all companies:")
        for filing in global_filings:
            print(f"  - {filing}")
    except Exception as e:
        print(f"Global filings search not fully implemented: {e}")
    
    # 7. Get company facts
    print("\n7. Getting company facts...")
    try:
        facts = company.get_company_facts()
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        print(f"Available US-GAAP facts: {len(us_gaap)}")
        
        # Show some key financial metrics
        key_metrics = ["Assets", "Liabilities", "StockholdersEquity", "Revenues"]
        for metric in key_metrics:
            if metric in us_gaap:
                units = us_gaap[metric].get("units", {})
                if "USD" in units and units["USD"]:
                    latest_value = units["USD"][-1].get("val")
                    print(f"  {metric}: ${latest_value:,.0f}" if latest_value else f"  {metric}: No value")
                    
    except Exception as e:
        print(f"Could not get company facts: {e}")


if __name__ == "__main__":
    main()