# SEC EDGAR Toolkit - TypeScript/JavaScript

TypeScript/JavaScript library for accessing SEC EDGAR filing data.

## Installation

```bash
pnpm add sec-edgar-toolkit
# or
npm install sec-edgar-toolkit
# or
yarn add sec-edgar-toolkit
```

## Quick Start

```typescript
import { EdgarClient, Form4Parser } from 'sec-edgar-toolkit';

// Initialize client with required User-Agent
const client = new EdgarClient({
  userAgent: 'MyCompany/1.0 (contact@example.com)'
});

// Search for company by ticker
const company = await client.getCompanyByTicker('AAPL');
console.log(`Apple Inc. CIK: ${company?.cik_str}`);

// Get recent filings
if (company) {
  const submissions = await client.getCompanySubmissions(company.cik_str);
  console.log(`Total filings: ${submissions.filings.recent.form.length}`);
}

// Parse SEC ownership forms (Forms 3, 4, 5)
const xmlContent = '<ownershipDocument>...</ownershipDocument>';
const parser = new Form4Parser(xmlContent);
const parsedData = parser.parseAll();
console.log('Parsed insider transaction:', parsedData.nonDerivativeTransactions[0]);
```

## Environment Variables

You can set your User-Agent as an environment variable instead of passing it to the constructor:

```bash
export SEC_EDGAR_TOOLKIT_USER_AGENT="MyCompany/1.0 (contact@example.com)"
```

## API Reference

### EdgarClient

#### Constructor

```typescript
new EdgarClient(config?: EdgarClientConfig)
```

**Config Options:**
- `userAgent?: string` - Required User-Agent with contact info
- `rateLimitDelay?: number` - Delay between requests in seconds (default: 0.1)
- `maxRetries?: number` - Max retry attempts (default: 3)
- `timeout?: number` - Request timeout in milliseconds (default: 30000)

#### Company Methods

##### getCompanyByTicker(ticker: string)
Search for company by ticker symbol.

```typescript
const company = await client.getCompanyByTicker('MSFT');
// Returns: CompanyTicker | null
```

##### getCompanyByCik(cik: string | number)
Get company by CIK (Central Index Key).

```typescript
const company = await client.getCompanyByCik('0000789019');
// Returns: CompanyTicker | null
```

##### searchCompanies(query: string)
Search companies by name or ticker.

```typescript
const companies = await client.searchCompanies('Apple');
// Returns: CompanyTicker[]
```

#### Filing Methods

##### getCompanySubmissions(cik: string | number, options?: RequestOptions)
Get all submissions for a company.

```typescript
const submissions = await client.getCompanySubmissions('0000320193', {
  submissionType: '10-K',
  fromDate: '2023-01-01',
  toDate: '2023-12-31'
});
// Returns: CompanySubmissions
```

##### getFiling(cik: string | number, accessionNumber: string)
Get specific filing details.

```typescript
const filing = await client.getFiling('0000320193', '0000320193-23-000106');
// Returns: Record<string, any>
```

#### XBRL Methods

##### getCompanyFacts(cik: string | number)
Get XBRL facts data for a company.

```typescript
const facts = await client.getCompanyFacts('0000320193');
// Returns: Record<string, any>
```

##### getCompanyConcept(cik: string | number, taxonomy: string, tag: string, unit?: string)
Get specific XBRL concept data.

```typescript
const concept = await client.getCompanyConcept(
  '0000320193',
  'us-gaap',
  'Assets',
  'USD'
);
// Returns: Record<string, any>
```

##### getFrames(taxonomy: string, tag: string, unit: string, year: number, options?: RequestOptions)
Get aggregated XBRL data for all companies.

```typescript
const frames = await client.getFrames('us-gaap', 'Assets', 'USD', 2023, {
  quarter: 4
});
// Returns: Record<string, any>
```

## XML Parsing

The library includes parsers for SEC ownership forms (Forms 3, 4, and 5) which contain insider transaction data.

### Ownership Form Parsers

```typescript
import { OwnershipFormParser, Form4Parser, Form5Parser } from 'sec-edgar-toolkit';

// General parser (auto-detects form type)
const parser = new OwnershipFormParser(xmlContent);
const data = parser.parseAll();

// Specialized parsers
const form4Parser = new Form4Parser(xmlContent);
const form5Parser = new Form5Parser(xmlContent);

// Parse specific sections
const documentInfo = parser.parseDocumentInfo();
const issuerInfo = parser.parseIssuerInfo();
const transactions = parser.parseNonDerivativeTransactions();
const holdings = parser.parseNonDerivativeHoldings();
const derivatives = parser.parseDerivativeTransactions();
```

### Parsed Data Structure

```typescript
interface ParsedOwnershipForm {
  documentInfo: DocumentInfo;
  issuerInfo: IssuerInfo;
  reportingOwnerInfo: ReportingOwnerInfo;
  nonDerivativeTransactions: NonDerivativeTransaction[];
  nonDerivativeHoldings: NonDerivativeHolding[];
  derivativeTransactions: DerivativeTransaction[];
}
```

## Types

### CompanyTicker
```typescript
interface CompanyTicker {
  cik_str: string;
  ticker: string;
  title: string;
  exchange?: string;
}
```

### CompanySubmissions
```typescript
interface CompanySubmissions {
  cik: string;
  entityType: string;
  name: string;
  tickers: string[];
  exchanges: string[];
  filings: Record<string, any>;
  // ... additional properties
}
```

## Error Handling

The library includes specific error types:

```typescript
import { SecEdgarApiError, RateLimitError, NotFoundError } from 'sec-edgar-toolkit';

try {
  const company = await client.getCompanyByTicker('INVALID');
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log('Rate limit exceeded, please wait');
  } else if (error instanceof NotFoundError) {
    console.log('Company not found');
  } else if (error instanceof SecEdgarApiError) {
    console.log(`API error: ${error.message}`);
  }
}
```

## Rate Limiting

The client automatically implements rate limiting to comply with SEC's 10 requests per second limit. You can adjust the delay:

```typescript
const client = new EdgarClient({
  userAgent: 'MyApp/1.0 (contact@example.com)',
  rateLimitDelay: 0.2 // 200ms delay between requests
});
```

## Development

```bash
# Install dependencies
pnpm install

# Build the library
pnpm run build

# Run tests
pnpm run test

# Run linter
pnpm run lint

# Format code
pnpm run format
```

## License

MIT License