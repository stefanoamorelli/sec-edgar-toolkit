/**
 * SEC EDGAR Toolkit - TypeScript/JavaScript library for accessing SEC EDGAR filing data
 *
 * Three layers, from most to least convenient:
 *
 * 1. Object API (primary): `Company`, `Filing`, and module-level helpers
 *
 *    ```ts
 *    import { Company, setIdentity } from 'sec-edgar-toolkit';
 *
 *    setIdentity('MyApp/1.0 (me@example.com)');
 *    const apple = await Company.lookup('AAPL');
 *    const latest10K = (await apple.getFilings({ form: '10-K' })).latest();
 *    ```
 *
 * 2. Fluent client: chainable query builders (`createClient`, in `./edgar`).
 *
 * 3. Low-level client: raw SEC JSON endpoints (`EdgarClient`).
 */

// Object API - primary interface
export {
  Attachment,
  Company,
  CompanyFacts,
  EightK,
  FactRow,
  Filing,
  FilingObject,
  FilingProps,
  Filings,
  Financials,
  GetFilingsOptions,
  GlobalGetFilingsOptions,
  OwnershipForm,
  OwnershipHolding,
  OwnershipTransaction,
  PeriodicReport,
  ReportFiling,
  StatementRow,
  StatementTable,
  TenK,
  TenQ,
  XBRLInstance,
  RenderedReportReader,
  ReportDescriptor,
  StatementLineItem,
  FactHistoryRow,
  findCompany,
  getApi,
  getCurrentFilings,
  getFilings,
  search,
  setIdentity,
} from "./core";

// Low-level API client
export { EdgarClient, SyncEdgarClient } from "./client";

// Fluent API (its Company/Filing classes stay namespaced in ./edgar)
export { createClient } from "./edgar";

// Endpoint modules
export * from "./endpoints";

// Utilities
export * from "./utils";

// Type definitions
export * from "./types";

// Exceptions
export * from "./exceptions";

// Parsers
export * from "./parsers";
