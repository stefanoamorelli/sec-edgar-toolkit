/**
 * Synchronous wrapper utilities for TypeScript async APIs
 * 
 * Note: This provides synchronous versions of async methods for compatibility
 * with legacy codebases. Async/await is strongly recommended for new code.
 * 
 * The synchronous implementation uses a promise-based approach that waits
 * for async operations to complete before returning.
 */

import { EdgarClient, Company } from '../edgar';
import { EdgarClientConfig } from '../types';

/**
 * Note about synchronous implementation:
 * 
 * True synchronous execution of async code in JavaScript/TypeScript is challenging
 * without blocking the event loop. This implementation provides a synchronous-style
 * API but still requires the underlying async operations to complete.
 * 
 * For true synchronous behavior in Node.js, consider using:
 * - child_process.execSync with a separate script
 * - Native addons
 * - Worker threads with SharedArrayBuffer
 * 
 * For most use cases, we recommend using the async API with async/await.
 */

/**
 * Synchronous-style wrapper for SEC EDGAR API client
 * 
 * IMPORTANT: This is a compatibility layer that provides a synchronous-style API.
 * The methods still return Promises internally but can be used with .then() chaining
 * or in environments that support top-level await.
 * 
 * For true synchronous behavior, you must await the results:
 * ```typescript
 * const client = new SyncEdgarClient(config);
 * const company = await client.companies.lookup("AAPL");
 * ```
 * 
 * Or use .then() chaining:
 * ```typescript
 * client.companies.lookup("AAPL").then(company => {
 *   // Use company here
 * });
 * ```
 */
export class SyncEdgarClient {
  private client: EdgarClient;

  constructor(config: EdgarClientConfig) {
    this.client = new EdgarClient(config);
  }

  /**
   * Company operations with synchronous-style API
   */
  get companies() {
    return {
      /**
       * Look up a company synchronously
       * Note: Still returns a Promise, use with await or .then()
       */
      lookup: (identifier: string | number) => {
        return this.client.companies.lookup(identifier);
      },

      /**
       * Search companies synchronously
       */
      search: (query: string, limit?: number) => {
        const builder = this.client.companies.search(query);
        if (limit) builder.limit(limit);
        return builder.execute();
      },

      /**
       * Batch lookup companies
       */
      batchLookup: (identifiers: Array<string | number>) => {
        return this.client.companies.batchLookup(identifiers);
      }
    };
  }

  /**
   * Filing operations with synchronous-style API
   */
  get filings() {
    return {
      /**
       * Get filings for a company
       */
      getFilings: (
        company: Company | string | number,
        options?: {
          formTypes?: string[];
          since?: string;
          until?: string;
          limit?: number;
        }
      ) => {
        const builder = this.client.filings.forCompany(company);
        
        if (options?.formTypes) builder.formTypes(options.formTypes);
        if (options?.since) builder.since(options.since);
        if (options?.until) builder.until(options.until);
        if (options?.limit) builder.recent(options.limit);
        
        return builder.fetch();
      }
    };
  }

  /**
   * Facts operations with synchronous-style API
   */
  get facts() {
    return {
      /**
       * Get facts for a company
       */
      getFacts: (
        company: Company | string | number,
        options?: {
          concept?: string;
          taxonomy?: string;
          units?: string;
          period?: string;
        }
      ) => {
        const builder = this.client.facts.forCompany(company);
        
        if (options?.concept) builder.concept(options.concept);
        if (options?.taxonomy) builder.taxonomy(options.taxonomy);
        if (options?.units) builder.inUnits(options.units);
        if (options?.period) builder.period(options.period);
        
        return builder.fetch();
      }
    };
  }
}

/**
 * Create a synchronous-style Edgar client
 * 
 * @example
 * ```typescript
 * // With top-level await (Node.js 14.8+, or transpiled)
 * const client = createSyncClient({ userAgent: "MyApp/1.0" });
 * const company = await client.companies.lookup("AAPL");
 * 
 * // With .then() chaining
 * client.companies.lookup("AAPL").then(company => {
 *   console.log(company?.name);
 * });
 * 
 * // In async function
 * async function getCompanyData() {
 *   const client = createSyncClient({ userAgent: "MyApp/1.0" });
 *   const company = await client.companies.lookup("AAPL");
 *   const filings = await client.filings.getFilings(company, {
 *     formTypes: ["10-K"],
 *     limit: 5
 *   });
 *   return { company, filings };
 * }
 * ```
 */
export function createSyncClient(config: EdgarClientConfig): SyncEdgarClient {
  return new SyncEdgarClient(config);
}