#!/usr/bin/env ts-node
/**
 * XBRL Financial Analysis Example
 * 
 * This example demonstrates how to use the SEC EDGAR Toolkit to:
 * 1. Find a company's latest 10-K filing
 * 2. Extract XBRL financial data
 * 3. Analyze key financial metrics
 */

import { createClient } from '../src';

async function main() {
    // Initialize the client
    const client = createClient({
        userAgent: 'FinancialAnalysisDemo/1.0 (demo@example.com)'
    });
    
    // Find Apple Inc.
    console.log('Finding Apple Inc...');
    const company = await client.companies.lookup('AAPL');
    
    if (!company) {
        console.error('Company not found!');
        return;
    }
    
    console.log(`Found: ${company.name} (CIK: ${company.cik})`);
    
    // Get the latest 10-K filing
    console.log('\nFetching latest 10-K filing...');
    const filings = await company.filings
        .formTypes(['10-K'])
        .recent(1)
        .fetch();
    
    if (!filings || filings.length === 0) {
        console.error('No 10-K filings found!');
        return;
    }
    
    const latest10K = filings[0];
    console.log(`Found filing: ${latest10K.formType} filed on ${latest10K.filingDate}`);
    
    // Extract XBRL data
    console.log('\nExtracting XBRL financial data...');
    const xbrl = await latest10K.xbrl();
    
    // Get key financial metrics
    console.log('\nKey Financial Metrics:');
    console.log('='.repeat(50));
    
    // Revenue
    const revenue = await xbrl.getConceptValue('Revenues');
    if (revenue) {
        console.log(`Total Revenue: $${revenue.toLocaleString()}`);
    }
    
    // Net Income
    const netIncome = await xbrl.getConceptValue('NetIncomeLoss');
    if (netIncome) {
        console.log(`Net Income: $${netIncome.toLocaleString()}`);
    }
    
    // Total Assets
    const assets = await xbrl.getConceptValue('Assets');
    if (assets) {
        console.log(`Total Assets: $${assets.toLocaleString()}`);
    }
    
    // Total Liabilities
    const liabilities = await xbrl.getConceptValue('Liabilities');
    if (liabilities) {
        console.log(`Total Liabilities: $${liabilities.toLocaleString()}`);
    }
    
    // Stockholders' Equity
    const equity = await xbrl.getConceptValue('StockholdersEquity');
    if (equity) {
        console.log(`Stockholders' Equity: $${equity.toLocaleString()}`);
    }
    
    // Cash and Cash Equivalents
    const cash = await xbrl.getConceptValue('CashAndCashEquivalentsAtCarryingValue');
    if (cash) {
        console.log(`Cash and Cash Equivalents: $${cash.toLocaleString()}`);
    }
    
    // Calculate some ratios
    console.log('\nFinancial Ratios:');
    console.log('='.repeat(50));
    
    if (assets && liabilities) {
        const debtToAssets = liabilities / assets;
        console.log(`Debt-to-Assets Ratio: ${(debtToAssets * 100).toFixed(2)}%`);
    }
    
    if (revenue && netIncome) {
        const profitMargin = netIncome / revenue;
        console.log(`Profit Margin: ${(profitMargin * 100).toFixed(2)}%`);
    }
    
    if (assets && equity && netIncome) {
        const returnOnEquity = netIncome / equity;
        console.log(`Return on Equity (ROE): ${(returnOnEquity * 100).toFixed(2)}%`);
    }
    
    // Get financial statements
    console.log('\nFinancial Statements:');
    console.log('='.repeat(50));
    
    try {
        // Get balance sheet
        const balanceSheet = await xbrl.getBalanceSheet();
        console.log('\nBalance Sheet Summary:');
        console.log(`  Current Assets: $${balanceSheet.assets.current?.toLocaleString() || 'N/A'}`);
        console.log(`  Non-Current Assets: $${balanceSheet.assets.nonCurrent?.toLocaleString() || 'N/A'}`);
        console.log(`  Current Liabilities: $${balanceSheet.liabilities.current?.toLocaleString() || 'N/A'}`);
        console.log(`  Non-Current Liabilities: $${balanceSheet.liabilities.nonCurrent?.toLocaleString() || 'N/A'}`);
        
        // Get income statement
        const incomeStatement = await xbrl.getIncomeStatement();
        console.log('\nIncome Statement Summary:');
        console.log(`  Gross Profit: $${incomeStatement.grossProfit?.toLocaleString() || 'N/A'}`);
        console.log(`  Operating Income: $${incomeStatement.operatingIncome?.toLocaleString() || 'N/A'}`);
        console.log(`  Income Before Tax: $${incomeStatement.incomeBeforeTax?.toLocaleString() || 'N/A'}`);
        console.log(`  Tax Expense: $${incomeStatement.incomeTaxExpense?.toLocaleString() || 'N/A'}`);
        
        // Get cash flow statement
        const cashFlow = await xbrl.getCashFlowStatement();
        console.log('\nCash Flow Statement Summary:');
        console.log(`  Operating Cash Flow: $${cashFlow.operating.netCashFlow?.toLocaleString() || 'N/A'}`);
        console.log(`  Investing Cash Flow: $${cashFlow.investing.netCashFlow?.toLocaleString() || 'N/A'}`);
        console.log(`  Financing Cash Flow: $${cashFlow.financing.netCashFlow?.toLocaleString() || 'N/A'}`);
        
    } catch (error) {
        console.error('Error extracting financial statements:', error);
    }
}

// Run the example
main().catch(console.error);