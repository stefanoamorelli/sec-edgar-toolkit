/**
 * SEC EDGAR API Client
 * 
 * This module provides the main SEC EDGAR API client that combines all endpoint
 * modules into a single, easy-to-use interface.
 * 
 * Example:
 *   import { EdgarClient } from 'sec-edgar-toolkit';
 *   
 *   const client = new EdgarClient({ userAgent: 'MyApp/1.0 (contact@example.com)' });
 *   const company = await client.getCompanyByTicker('AAPL');
 *   const submissions = await client.getCompanySubmissions(company.cik_str);
 * 
 * Note:
 *   The SEC requires a User-Agent header with contact information for all API requests.
 *   Please provide accurate contact information in case the SEC needs to reach you
 *   about your usage.
 */

import { HttpClient } from '../utils';
import { CompanyEndpoints, FilingsEndpoints, XbrlEndpoints } from '../endpoints';
import {
  CompanyTicker,
  CompanySubmissions,
  EdgarClientConfig,
  RequestOptions
} from '../types';
import { InvalidUserAgentError } from '../exceptions/errors';

export class EdgarClient {
  private httpClient: HttpClient;
  private userAgent: string;

  // Endpoint modules
  public company: CompanyEndpoints;
  public filings: FilingsEndpoints;
  public xbrl: XbrlEndpoints;

  constructor(config: EdgarClientConfig = {}) {
    // Get user agent from config or environment variable
    const userAgent = config.userAgent || process.env.SEC_EDGAR_TOOLKIT_USER_AGENT;
    
    if (!userAgent) {
      throw new InvalidUserAgentError();
    }

    if (userAgent.length < 10) {
      throw new InvalidUserAgentError(userAgent);
    }

    this.userAgent = userAgent;
    this.httpClient = new HttpClient(userAgent, {
      rateLimitDelay: config.rateLimitDelay,
      maxRetries: config.maxRetries,
      timeout: config.timeout,
      cache: config.cache !== false ? {
        ttl: 300000, // 5 minutes default
        maxSize: 500,
      } : false,
    });

    // Initialize endpoint modules
    this.company = new CompanyEndpoints(this.httpClient);
    this.filings = new FilingsEndpoints(this.httpClient);
    this.xbrl = new XbrlEndpoints(this.httpClient);
  }

  // Convenience methods that delegate to endpoint modules

  // Company methods
  async getCompanyTickers(forceRefresh: boolean = false): Promise<Record<string, any>> {
    return this.company.getCompanyTickers(forceRefresh);
  }

  async getCompanyByTicker(ticker: string): Promise<CompanyTicker | null> {
    return this.company.getCompanyByTicker(ticker);
  }

  async getCompanyByCik(cik: string | number): Promise<CompanyTicker | null> {
    return this.company.getCompanyByCik(cik);
  }

  async searchCompanies(query: string): Promise<CompanyTicker[]> {
    return this.company.searchCompanies(query);
  }

  // Filing methods
  async getCompanySubmissions(
    cik: string | number,
    options: RequestOptions = {}
  ): Promise<CompanySubmissions> {
    return this.filings.getCompanySubmissions(cik, options);
  }

  async getFiling(cik: string | number, accessionNumber: string): Promise<Record<string, any>> {
    return this.filings.getFiling(cik, accessionNumber);
  }

  // XBRL methods
  async getCompanyFacts(cik: string | number): Promise<Record<string, any>> {
    return this.xbrl.getCompanyFacts(cik);
  }

  async getCompanyConcept(
    cik: string | number,
    taxonomy: string,
    tag: string,
    unit?: string
  ): Promise<Record<string, any>> {
    return this.xbrl.getCompanyConcept(cik, taxonomy, tag, unit);
  }

  async getFrames(
    taxonomy: string,
    tag: string,
    unit: string,
    year: number,
    options: RequestOptions = {}
  ): Promise<Record<string, any>> {
    return this.xbrl.getFrames(taxonomy, tag, unit, year, options);
  }
}