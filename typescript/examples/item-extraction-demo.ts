#!/usr/bin/env ts-node
/**
 * Demo of SEC filing item extraction functionality.
 * 
 * This example shows how to extract individual items from SEC filings
 * similar to the edgar-crawler functionality.
 */

import { createClient } from '../typescript/src';
import * as fs from 'fs/promises';

async function main() {
  // Initialize the client
  const client = createClient({
    userAgent: "ItemExtractionDemo/1.0 (demo@example.com)"
  });
  
  // Find Apple Inc.
  console.log("Finding Apple Inc...");
  const company = await client.companies.lookup("AAPL");
  
  if (!company) {
    console.log("Company not found!");
    return;
  }
  
  console.log(`Found: ${company}`);
  
  // Get the latest 10-K filing
  console.log("\nFetching latest 10-K filing...");
  const filings = await company.filings
    .formTypes(["10-K"])
    .recent(1)
    .fetch();
  
  if (!filings || filings.length === 0) {
    console.log("No 10-K filings found!");
    return;
  }
  
  const latest10k = filings[0];
  console.log(`Found filing: ${latest10k.formType} from ${latest10k.filingDate}`);
  
  // Extract all items
  console.log("\nExtracting all items from the filing...");
  const items = await latest10k.extractItems();
  
  // Display summary of extracted items
  console.log(`\nExtracted ${Object.keys(items).length} items:`);
  for (const [itemNum, content] of Object.entries(items)) {
    const contentPreview = content ? content.substring(0, 100).replace(/\n/g, ' ') : "[Empty]";
    console.log(`  Item ${itemNum}: ${content.length} chars - ${contentPreview}...`);
  }
  
  // Extract specific items
  console.log("\nExtracting specific items (1, 1A, 7)...");
  const specificItems = await latest10k.extractItems(["1", "1A", "7"]);
  
  // Save to JSON format similar to edgar-crawler
  const output = {
    filename: `${company.cik}_${latest10k.formType}_${latest10k.filingDate}_${latest10k.accessionNumber}.htm`,
    company: company.name,
    cik: company.cik,
    filing_date: latest10k.filingDate,
    form_type: latest10k.formType,
    accession_number: latest10k.accessionNumber,
  };
  
  // Add item content with edgar-crawler style keys
  for (const [itemNum, content] of Object.entries(items)) {
    const key = `item_${itemNum}`.replace(".", "_");
    output[key] = content;
  }
  
  // Save to file
  const outputFilename = `extracted_items_${company.ticker}_${latest10k.formType}.json`;
  await fs.writeFile(outputFilename, JSON.stringify(output, null, 2), 'utf-8');
  
  console.log(`\nSaved extracted items to ${outputFilename}`);
  
  // Example of using the convenience methods
  console.log("\nUsing convenience methods:");
  const riskFactors = await latest10k.getItem("1A");
  if (riskFactors) {
    console.log(`Risk Factors length: ${riskFactors.length} characters`);
    console.log(`First 200 chars: ${riskFactors.substring(0, 200)}...`);
  }
  
  // Access all items via property
  const allItems = await latest10k.items;
  console.log(`\nTotal items available: ${Object.keys(allItems).length}`);
}

// Run the demo
main().catch(console.error);