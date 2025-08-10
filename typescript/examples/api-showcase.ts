/**
 * SEC EDGAR Toolkit API Showcase - TypeScript
 * 
 * This example demonstrates the fluent interface for accessing
 * SEC filing data with a chainable, type-safe API design.
 */

import { 
  createClient, 
  EdgarClient, 
  Company, 
  Filing,
  EdgarClientConfig 
} from '../src/edgar';

async function main(): Promise<void> {
  console.log('🚀 SEC EDGAR Toolkit - TypeScript API Showcase');
  console.log('='.repeat(55));

  // Initialize client with fluent configuration
  const config: EdgarClientConfig = {
    userAgent: process.env.SEC_EDGAR_TOOLKIT_USER_AGENT || 'TSShowcase/1.0 (demo@example.com)',
    rateLimitDelay: 0.1,
    timeout: 30000,
  };

  const client = createClient(config).configure({
    rateLimitDelay: 0.15, // Fine-tune settings
  });

  // 1. Company lookup with full type safety
  console.log('\n1. Company Discovery & Analysis');
  console.log('-'.repeat(30));

  const company = await client.companies.lookup('AAPL');
  if (company) {
    console.log(`Found: ${company}`);
    console.log(`  CIK: ${company.cik}`);
    console.log(`  Exchange: ${company.exchange}`);

    // Get financial summary using fluent API
    const summary = await company.getFinancialSummary();
    if (summary.totalAssets) {
      console.log(`  Total Assets: $${summary.totalAssets.toLocaleString()}`);
    }
    if (summary.totalStockholdersEquity) {
      console.log(`  Total Equity: $${summary.totalStockholdersEquity.toLocaleString()}`);
    }
  }

  // 2. Advanced company search with type-safe filters
  console.log('\n2. Advanced Company Search');
  console.log('-'.repeat(30));

  const techCompanies = await client.companies
    .search('technology')
    .limit(3)
    .execute();

  console.log(`Found ${techCompanies.length} technology companies:`);
  techCompanies.forEach((comp, i) => {
    console.log(`  ${i + 1}. ${comp}`);
  });

  // 3. Fluent filing queries with strong typing
  console.log('\n3. Fluent Filing Queries');
  console.log('-'.repeat(30));

  if (company) {
    // Chain multiple filters for precise queries
    const recentFilings = await company.filings
      .formTypes(['10-K', '10-Q'])
      .recent(3)
      .fetch();

    console.log(`Recent financial filings for ${company.ticker}:`);
    for (const filing of recentFilings) {
      console.log(`  • ${filing.formType} filed on ${filing.filingDate}`);

      // Quick content preview
      const preview = await filing.preview(200);
      if (preview) {
        console.log(`    Preview: ${preview}`);
      }
    }
  }

  // 4. Advanced XBRL data queries
  console.log('\n4. Advanced Financial Data Queries');
  console.log('-'.repeat(30));

  if (company) {
    // Query specific financial concepts with filters
    const assetsData = await company.facts
      .concept('Assets')
      .inUnits('USD')
      .fetch();

    if (assetsData.length > 0) {
      const latestAssets = assetsData.reduce((latest, fact) => 
        (fact.filed > latest.filed) ? fact : latest
      );
      
      console.log(`Latest Assets: $${latestAssets.value?.toLocaleString()}`);
      console.log(`  Filed: ${latestAssets.filed || 'N/A'}`);
      console.log(`  Period: ${latestAssets.period || 'N/A'}`);
    }

    // Get latest filing with content analysis
    const latest10K = await company.getLatestFiling('10-K');
    if (latest10K) {
      console.log(`\nLatest 10-K: ${latest10K}`);

      // Analyze filing content
      const financials = await latest10K.analysis.extractFinancials();
      if (financials) {
        const ratios = await financials.getKeyRatios();
        console.log('Key Financial Ratios:');
        
        Object.entries(ratios).forEach(([ratioName, value]) => {
          if (value !== undefined) {
            console.log(`  ${ratioName}: ${value.toFixed(3)}`);
          }
        });
      }
    }
  }

  // 5. Batch operations with Promise.all
  console.log('\n5. Batch Operations');
  console.log('-'.repeat(30));

  const tickers = ['AAPL', 'MSFT', 'GOOGL'];
  const companies = await client.companies.batchLookup(tickers);

  console.log('Batch company lookup:');
  tickers.forEach((ticker, i) => {
    const comp = companies[i];
    if (comp) {
      console.log(`  ✓ ${ticker}: ${comp.name}`);
    } else {
      console.log(`  ✗ ${ticker}: Not found`);
    }
  });

  // 6. Cross-company filing analysis
  console.log('\n6. Cross-Company Analysis');
  console.log('-'.repeat(30));

  const filingCounts: Record<string, number> = {};
  
  for (const comp of companies) {
    if (comp) {
      const filings = await comp.filings
        .formTypes(['8-K'])
        .recent(5)
        .fetch();
      filingCounts[comp.ticker] = filings.length;
    }
  }

  console.log('Recent 8-K filing counts:');
  Object.entries(filingCounts).forEach(([ticker, count]) => {
    console.log(`  ${ticker}: ${count} filings`);
  });

  // 7. Advanced filtering and data processing
  console.log('\n7. Advanced Data Processing');
  console.log('-'.repeat(30));

  if (company) {
    // Get multiple financial metrics in parallel
    const [assets, liabilities, revenues] = await Promise.all([
      company.facts.concept('Assets').inUnits('USD').fetch(),
      company.facts.concept('Liabilities').inUnits('USD').fetch(),
      company.facts.concept('Revenues').inUnits('USD').fetch(),
    ]);

    console.log('Parallel financial data retrieval:');
    console.log(`  Assets entries: ${assets.length}`);
    console.log(`  Liabilities entries: ${liabilities.length}`);
    console.log(`  Revenues entries: ${revenues.length}`);

    // Calculate trends if we have multiple data points
    if (assets.length > 1) {
      const sortedAssets = assets
        .filter(a => a.value && a.fiscalYear)
        .sort((a, b) => (a.fiscalYear || 0) - (b.fiscalYear || 0));

      if (sortedAssets.length >= 2) {
        const latest = sortedAssets[sortedAssets.length - 1];
        const previous = sortedAssets[sortedAssets.length - 2];
        
        if (latest.value && previous.value) {
          const growth = ((latest.value - previous.value) / previous.value) * 100;
          console.log(`  Asset growth (${previous.fiscalYear} → ${latest.fiscalYear}): ${growth.toFixed(1)}%`);
        }
      }
    }
  }
}

// Advanced error handling demonstration
async function errorHandlingDemo(): Promise<void> {
  console.log('\n8. Error Handling & Resilience');
  console.log('-'.repeat(30));

  const client = createClient({
    userAgent: 'ErrorDemo/1.0 (demo@example.com)',
    timeout: 5000, // Short timeout for demo
  });

  try {
    // Attempt to lookup non-existent company
    const company = await client.companies.lookup('INVALID_TICKER');
    console.log(company ? '  Found company' : '  ✓ Gracefully handled missing company');

    // Attempt operations with error recovery
    const companies = await client.companies.batchLookup(['AAPL', 'INVALID', 'MSFT']);
    const validCompanies = companies.filter(c => c !== null);
    console.log(`  ✓ Batch operation: ${validCompanies.length}/3 companies found`);

  } catch (error) {
    console.log(`  ✓ Error handled gracefully: ${error}`);
  }
}

// Run the showcase
async function runShowcase(): Promise<void> {
  try {
    await main();
    await errorHandlingDemo();

    console.log('\n✨ TypeScript API showcase completed!');
    console.log('\nKey advantages of this API design:');
    console.log('• Full TypeScript type safety with IntelliSense support');
    console.log('• Fluent, chainable interface for intuitive usage');
    console.log('• Native async/await with Promise-based operations');
    console.log('• Comprehensive error handling and graceful degradation');
    console.log('• Optimized for JavaScript/TypeScript applications');
    console.log('• Rich financial data analysis with type-safe results');

  } catch (error) {
    console.error('Showcase failed:', error);
    process.exit(1);
  }
}

// Execute if this file is run directly
if (require.main === module) {
  runShowcase();
}

export { runShowcase };