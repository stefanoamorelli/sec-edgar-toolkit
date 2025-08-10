#!/usr/bin/env python3
"""
Current Events Tracker Example

This example demonstrates how to use the SEC EDGAR Toolkit to:
1. Monitor recent 8-K filings for a company
2. Extract and analyze current events
3. Identify material changes and important disclosures
"""

import asyncio
from datetime import datetime, timedelta
from sec_edgar_toolkit import create_client


async def main():
    # Initialize the client
    client = create_client("CurrentEventsTracker/1.0 (demo@example.com)")
    
    # Track multiple companies
    companies_to_track = ["AAPL", "TSLA", "NVDA", "AMZN"]
    
    print("Current Events Tracker")
    print("=" * 80)
    print(f"Tracking 8-K filings for: {', '.join(companies_to_track)}")
    print(f"Date range: Last 30 days\n")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    for ticker in companies_to_track:
        print(f"\n{ticker}")
        print("-" * 40)
        
        # Find company
        company = await client.companies.lookup(ticker)
        if not company:
            print(f"Company {ticker} not found!")
            continue
        
        # Get recent 8-K filings
        filings = await (company.filings
                        .form_types(["8-K"])
                        .since(start_date.strftime("%Y-%m-%d"))
                        .fetch())
        
        if not filings:
            print(f"No 8-K filings in the last 30 days")
            continue
        
        print(f"Found {len(filings)} 8-K filing(s)")
        
        # Analyze each filing
        for filing in filings[:3]:  # Limit to most recent 3
            print(f"\n  Filing Date: {filing.filing_date}")
            
            try:
                # Get filing content
                content = await filing.text()
                
                # Extract current events
                events = await filing.get_current_events()
                
                if events:
                    print("  Events reported:")
                    for event in events:
                        print(f"    - Item {event.item_number}: {event.title}")
                        
                        # Show key details based on event type
                        if "1.01" in event.item_number:  # Entry into Material Agreement
                            print("      → Material agreement entered")
                        elif "2.02" in event.item_number:  # Results of Operations
                            print("      → Financial results disclosed")
                        elif "5.02" in event.item_number:  # Officer Changes
                            print("      → Executive changes announced")
                        elif "7.01" in event.item_number:  # Regulation FD
                            print("      → Fair disclosure event")
                        elif "8.01" in event.item_number:  # Other Events
                            # Extract key phrases from content
                            content_preview = event.content[:200].replace('\n', ' ')
                            print(f"      → {content_preview}...")
                else:
                    print("  No structured events found")
                    
            except Exception as e:
                print(f"  Error analyzing filing: {str(e)}")
    
    # Summary of material events
    print("\n\nSummary of Material Events")
    print("=" * 80)
    print("Monitor these filings regularly to stay informed about:")
    print("- Material agreements and contracts")
    print("- Financial results and guidance updates")
    print("- Executive changes and board appointments")
    print("- Mergers, acquisitions, and strategic transactions")
    print("- Regulatory matters and compliance updates")


if __name__ == "__main__":
    asyncio.run(main())