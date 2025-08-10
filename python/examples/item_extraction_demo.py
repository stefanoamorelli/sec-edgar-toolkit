#!/usr/bin/env python3
"""
Demo of SEC filing item extraction functionality.

This example shows how to extract individual items from SEC filings
similar to the edgar-crawler functionality.
"""

import asyncio
import json
from sec_edgar_toolkit import create_client


async def main():
    # Initialize the client
    client = create_client("ItemExtractionDemo/1.0 (demo@example.com)")
    
    # Find Apple Inc.
    print("Finding Apple Inc...")
    company = await client.companies.lookup("AAPL")
    
    if not company:
        print("Company not found!")
        return
        
    print(f"Found: {company}")
    
    # Get the latest 10-K filing
    print("\nFetching latest 10-K filing...")
    filings = await (company.filings
                     .form_types(["10-K"])
                     .recent(1)
                     .fetch())
    
    if not filings:
        print("No 10-K filings found!")
        return
        
    latest_10k = filings[0]
    print(f"Found filing: {latest_10k.form_type} from {latest_10k.filing_date}")
    
    # Extract all items
    print("\nExtracting all items from the filing...")
    items = await latest_10k.extract_items()
    
    # Display summary of extracted items
    print(f"\nExtracted {len(items)} items:")
    for item_num, content in items.items():
        content_preview = content[:100].replace('\n', ' ') if content else "[Empty]"
        print(f"  Item {item_num}: {len(content)} chars - {content_preview}...")
    
    # Extract specific items
    print("\nExtracting specific items (1, 1A, 7)...")
    specific_items = await latest_10k.extract_items(["1", "1A", "7"])
    
    # Save to JSON format similar to edgar-crawler
    output = {
        "filename": f"{company.cik}_{latest_10k.form_type}_{latest_10k.filing_date}_{latest_10k.accession_number}.htm",
        "company": company.name,
        "cik": company.cik,
        "filing_date": latest_10k.filing_date,
        "form_type": latest_10k.form_type,
        "accession_number": latest_10k.accession_number,
    }
    
    # Add item content with edgar-crawler style keys
    for item_num, content in items.items():
        key = f"item_{item_num}".replace(".", "_")
        output[key] = content
    
    # Save to file
    output_filename = f"extracted_items_{company.ticker}_{latest_10k.form_type}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved extracted items to {output_filename}")
    
    # Example of using the convenience methods
    print("\nUsing convenience methods:")
    risk_factors = await latest_10k.get_item("1A")
    if risk_factors:
        print(f"Risk Factors length: {len(risk_factors)} characters")
        print(f"First 200 chars: {risk_factors[:200]}...")
    
    # Access all items via property
    all_items = await latest_10k.items
    print(f"\nTotal items available: {len(all_items)}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())