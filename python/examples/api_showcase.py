"""
SEC EDGAR Toolkit API Showcase

This example demonstrates the fluent interface for accessing
SEC filing data with a chainable, type-safe API design.
"""

import asyncio
import os
from sec_edgar_toolkit import EdgarClient, create_client, AsyncEdgarClient


def main():
    """Demonstrate the modern fluent API."""
    
    # Initialize client with fluent configuration
    user_agent = os.getenv("SEC_EDGAR_TOOLKIT_USER_AGENT", "Showcase/1.0 (demo@example.com)")
    
    client = create_client(user_agent).configure(
        rate_limit_delay=0.1,
        timeout=30
    )
    
    print("🚀 SEC EDGAR Toolkit - API Showcase")
    print("=" * 50)
    
    # 1. Company lookup with fluent interface
    print("\n1. Company Discovery & Analysis")
    print("-" * 30)
    
    company = client.companies.lookup("AAPL")
    if company:
        print(f"Found: {company}")
        print(f"  CIK: {company.cik}")
        print(f"  Exchange: {company.exchange}")
        
        # Get financial summary using fluent API
        summary = company.financial_summary()
        if summary:
            print(f"  Total Assets: ${summary.get('total_assets', 0):,.0f}")
            print(f"  Total Equity: ${summary.get('total_stockholdersequity', 0):,.0f}")
    
    # 2. Advanced company search with filters
    print("\n2. Advanced Company Search")
    print("-" * 30)
    
    tech_companies = (client.companies
                     .search("technology")
                     .limit(3)
                     .execute())
    
    print(f"Found {len(tech_companies)} technology companies:")
    for i, comp in enumerate(tech_companies, 1):
        print(f"  {i}. {comp}")
    
    # 3. Fluent filing queries
    print("\n3. Fluent Filing Queries")
    print("-" * 30)
    
    if company:
        # Chain multiple filters for precise queries
        recent_filings = (company.filings
                         .form_types(["10-K", "10-Q"])
                         .recent(3)
                         .fetch())
        
        print(f"Recent financial filings for {company.ticker}:")
        for filing in recent_filings:
            print(f"  • {filing.form_type} filed on {filing.filing_date}")
            
            # Quick content preview
            preview = filing.preview(200)
            if preview:
                print(f"    Preview: {preview}")
    
    # 4. Advanced XBRL data queries
    print("\n4. Advanced Financial Data Queries")
    print("-" * 30)
    
    if company:
        # Query specific financial concepts with filters
        assets_data = (company.facts
                      .concept("Assets")
                      .in_units("USD")
                      .fetch())
        
        if assets_data:
            latest_assets = max(assets_data, key=lambda x: x.get("filed", ""))
            print(f"Latest Assets: ${latest_assets.get('value', 0):,.0f}")
            print(f"  Filed: {latest_assets.get('filed', 'N/A')}")
            print(f"  Period: {latest_assets.get('period', 'N/A')}")
        
        # Get latest filing with content analysis
        latest_10k = company.get_latest_filing("10-K")
        if latest_10k:
            print(f"\nLatest 10-K: {latest_10k}")
            
            # Analyze filing content
            financials = latest_10k.analysis.extract_financials()
            if financials:
                ratios = financials.key_ratios()
                print(f"Key Financial Ratios:")
                for ratio_name, value in ratios.items():
                    if value:
                        print(f"  {ratio_name}: {value:.3f}")
    
    # 5. Batch operations
    print("\n5. Batch Operations")
    print("-" * 30)
    
    tickers = ["AAPL", "MSFT", "GOOGL"]
    companies = client.companies.batch_lookup(tickers)
    
    print("Batch company lookup:")
    for ticker, comp in zip(tickers, companies):
        if comp:
            print(f"  ✓ {ticker}: {comp.name}")
        else:
            print(f"  ✗ {ticker}: Not found")
    
    # 6. Cross-company filing analysis
    print("\n6. Cross-Company Analysis")
    print("-" * 30)
    
    filing_counts = {}
    for comp in companies:
        if comp:
            filings = comp.filings.form_types(["8-K"]).recent(5).fetch()
            filing_counts[comp.ticker] = len(filings)
    
    print("Recent 8-K filing counts:")
    for ticker, count in filing_counts.items():
        print(f"  {ticker}: {count} filings")


async def async_demo():
    """Demonstrate async capabilities."""
    
    print("\n7. Async Operations Demo")
    print("-" * 30)
    
    user_agent = os.getenv("SEC_EDGAR_TOOLKIT_USER_AGENT", "AsyncDemo/1.0 (demo@example.com)")
    async_client = AsyncEdgarClient(user_agent)
    
    # Async company lookup
    company = await async_client.lookup_company("AAPL")
    if company:
        print(f"Async lookup: {company}")
    
    # Async batch search
    results = await async_client.search_companies("tech", limit=2)
    print(f"Async search found {len(results)} companies")
    
    # Async context manager for batch operations
    async with async_client.batch_operations() as batch_client:
        tasks = [
            batch_client.lookup_company("AAPL"),
            batch_client.lookup_company("MSFT"),
            batch_client.search_companies("banking", limit=1)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"Batch operations completed: {len(results)} results")


if __name__ == "__main__":
    # Run synchronous demo
    main()
    
    # Run async demo
    try:
        asyncio.run(async_demo())
    except Exception as e:
        print(f"Async demo failed: {e}")
    
    print("\n✨ API showcase completed!")
    print("\nKey advantages of this API design:")
    print("• Fluent, chainable interface for intuitive usage")
    print("• Strong type safety and IDE autocomplete support")
    print("• Async/await support for applications")
    print("• Intelligent caching and rate limiting")
    print("• Comprehensive error handling")
    print("• Rich financial data analysis capabilities")