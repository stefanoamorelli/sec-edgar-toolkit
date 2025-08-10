#!/usr/bin/env python3
"""
Basic usage examples for the SEC EDGAR Toolkit.

This script demonstrates how to use the main features of the SEC EDGAR API client.
"""

import os
from datetime import datetime, timedelta

from sec_edgar_toolkit import SecEdgarApi, SecEdgarApiError


def main():
    """Demonstrate basic SEC EDGAR API usage."""
    # Initialize the API client 
    # The SEC requires a User-Agent header with contact info
    # This will be read from the SEC_EDGAR_TOOLKIT_USER_AGENT environment variable
    # Make sure to set SEC_EDGAR_TOOLKIT_USER_AGENT in your .env file or environment
    try:
        api = SecEdgarApi()  # Will read SEC_EDGAR_TOOLKIT_USER_AGENT from environment
    except EnvironmentError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please set the SEC_EDGAR_TOOLKIT_USER_AGENT environment variable or create a .env file.")
        print("Example: SEC_EDGAR_TOOLKIT_USER_AGENT='MyCompany/1.0 (contact@example.com)'")
        return

    try:
        print("🔍 SEC EDGAR Toolkit - Basic Usage Examples\n")

        # Example 1: Search for a company by ticker
        print("1. Finding Apple Inc. by ticker...")
        apple = api.get_company_by_ticker("AAPL")
        if apple:
            print(f"   Company: {apple['title']}")
            print(f"   CIK: {apple['cik_str']}")
            print(f"   Exchange: {apple.get('exchange', 'N/A')}")
        else:
            print("   Company not found!")

        print()

        # Example 2: Search companies by name
        print("2. Searching for companies with 'Apple' in the name...")
        results = api.search_companies("Apple")
        print(f"   Found {len(results)} companies:")
        for company in results[:3]:  # Show first 3 results
            print(f"   - {company['ticker']}: {company['title']}")

        print()

        # Example 3: Get company submissions (filings)
        if apple:
            print("3. Getting Apple's recent filings...")
            cik = apple['cik_str']
            submissions = api.get_company_submissions(cik)

            print(f"   Company: {submissions['name']}")
            print(f"   SIC: {submissions.get('sic')} - {submissions.get('sicDescription')}")
            print(f"   Website: {submissions.get('website', 'N/A')}")

            # Show recent filings
            recent_filings = submissions['filings']['recent']
            print(f"\n   Recent filings ({len(recent_filings['form'])} total):")
            for i in range(min(5, len(recent_filings['form']))):  # Show first 5
                form_type = recent_filings['form'][i]
                filing_date = recent_filings['filingDate'][i]
                print(f"   - {form_type} filed on {filing_date}")

        print()

        # Example 4: Filter filings by type and date
        if apple:
            print("4. Getting Apple's 10-K filings from the last 2 years...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2*365)  # 2 years ago

            annual_reports = api.get_company_submissions(
                cik,
                submission_type="10-K",
                from_date=start_date.strftime("%Y-%m-%d"),
                to_date=end_date.strftime("%Y-%m-%d")
            )

            annual_filings = annual_reports['filings']['recent']
            print(f"   Found {len(annual_filings['form'])} 10-K filings:")
            for i in range(len(annual_filings['form'])):
                filing_date = annual_filings['filingDate'][i]
                report_date = annual_filings['reportDate'][i]
                print(f"   - Filed: {filing_date}, Report Period: {report_date}")

        print()

        # Example 5: Get financial facts (XBRL data)
        if apple:
            print("5. Getting Apple's financial facts...")
            try:
                facts = api.get_company_facts(cik)

                if 'us-gaap' in facts['facts']:
                    gaap_facts = facts['facts']['us-gaap']
                    print(f"   Available US-GAAP concepts: {len(gaap_facts)}")

                    # Show some key financial metrics if available
                    key_metrics = ['Assets', 'Revenues', 'NetIncomeLoss']
                    for metric in key_metrics:
                        if metric in gaap_facts:
                            print(f"   - {metric}: Available")
                        else:
                            print(f"   - {metric}: Not available")

                else:
                    print("   No US-GAAP facts available")

            except SecEdgarApiError as e:
                print(f"   Error getting facts: {e}")

        print()

        # Example 6: Get specific concept data
        if apple:
            print("6. Getting Apple's total assets over time...")
            try:
                assets_data = api.get_company_concept(
                    cik,
                    taxonomy="us-gaap",
                    tag="Assets",
                    unit="USD"
                )

                if 'units' in assets_data and 'USD' in assets_data['units']:
                    usd_data = assets_data['units']['USD']
                    # Get last 3 annual reports
                    annual_data = [d for d in usd_data if d.get('fp') == 'FY'][-3:]

                    print("   Total Assets (Last 3 Annual Reports):")
                    for item in annual_data:
                        assets_billions = item['val'] / 1_000_000_000
                        print(f"   - FY {item['fy']}: ${assets_billions:.1f}B")

                else:
                    print("   No USD assets data available")

            except SecEdgarApiError as e:
                print(f"   Error getting assets data: {e}")

        print()

        # Example 7: Get market-wide data using frames
        print("7. Getting market-wide revenue data for 2023...")
        try:
            frame_data = api.get_frames(
                taxonomy="us-gaap",
                tag="Revenues",
                unit="USD",
                year=2023
            )

            companies_data = frame_data.get('data', [])
            print(f"   Total companies reporting: {len(companies_data)}")

            # Show top 5 companies by revenue
            if companies_data:
                sorted_companies = sorted(
                    companies_data,
                    key=lambda x: x.get('val', 0),
                    reverse=True
                )[:5]

                print("   Top 5 companies by annual revenue:")
                for i, company in enumerate(sorted_companies, 1):
                    name = company['entityName']
                    revenue_billions = company['val'] / 1_000_000_000
                    print(f"   {i}. {name}: ${revenue_billions:.1f}B")

        except SecEdgarApiError as e:
            print(f"   Error getting frame data: {e}")

        print("\n✅ Examples completed successfully!")

    except SecEdgarApiError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
