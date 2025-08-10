#!/usr/bin/env python3
"""
XBRL Financial Analysis Example

This example demonstrates how to use the SEC EDGAR Toolkit to:
1. Find a company's latest 10-K filing
2. Extract XBRL financial data
3. Analyze key financial metrics
"""

import asyncio
from sec_edgar_toolkit import create_client


async def main():
    # Initialize the client
    client = create_client("FinancialAnalysisDemo/1.0 (demo@example.com)")
    
    # Find Microsoft
    print("Finding Microsoft Corporation...")
    company = await client.companies.lookup("MSFT")
    
    if not company:
        print("Company not found!")
        return
        
    print(f"Found: {company.name} (CIK: {company.cik})")
    
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
    print(f"Found filing: {latest_10k.form_type} filed on {latest_10k.filing_date}")
    
    # Extract XBRL data
    print("\nExtracting XBRL financial data...")
    xbrl = await latest_10k.xbrl()
    
    # Get key financial metrics
    print("\nKey Financial Metrics:")
    print("=" * 50)
    
    # Revenue
    revenue = await xbrl.get_concept_value("Revenues")
    if revenue:
        print(f"Total Revenue: ${revenue:,.0f}")
    
    # Net Income
    net_income = await xbrl.get_concept_value("NetIncomeLoss")
    if net_income:
        print(f"Net Income: ${net_income:,.0f}")
    
    # Total Assets
    assets = await xbrl.get_concept_value("Assets")
    if assets:
        print(f"Total Assets: ${assets:,.0f}")
    
    # Total Liabilities
    liabilities = await xbrl.get_concept_value("Liabilities")
    if liabilities:
        print(f"Total Liabilities: ${liabilities:,.0f}")
    
    # Stockholders' Equity
    equity = await xbrl.get_concept_value("StockholdersEquity")
    if equity:
        print(f"Stockholders' Equity: ${equity:,.0f}")
    
    # Cash and Cash Equivalents
    cash = await xbrl.get_concept_value("CashAndCashEquivalentsAtCarryingValue")
    if cash:
        print(f"Cash and Cash Equivalents: ${cash:,.0f}")
    
    # Calculate some ratios
    print("\nFinancial Ratios:")
    print("=" * 50)
    
    if assets and liabilities:
        debt_to_assets = liabilities / assets
        print(f"Debt-to-Assets Ratio: {debt_to_assets:.2%}")
    
    if revenue and net_income:
        profit_margin = net_income / revenue
        print(f"Profit Margin: {profit_margin:.2%}")
    
    if assets and equity:
        return_on_equity = net_income / equity if net_income else 0
        print(f"Return on Equity (ROE): {return_on_equity:.2%}")
    
    # Get historical trends
    print("\nHistorical Revenue Trend (last 3 years):")
    print("=" * 50)
    
    # Get all revenue facts
    revenue_facts = await xbrl.get_facts_by_concept("Revenues")
    
    # Group by fiscal year
    yearly_revenues = {}
    for fact in revenue_facts:
        if fact.fiscal_year:
            yearly_revenues[fact.fiscal_year] = fact.value
    
    # Display sorted by year
    for year in sorted(yearly_revenues.keys())[-3:]:
        print(f"  {year}: ${yearly_revenues[year]:,.0f}")


if __name__ == "__main__":
    asyncio.run(main())