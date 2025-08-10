/**
 * SEC EDGAR API client with fluent interface design - TypeScript implementation
 * 
 * This module provides a comprehensive toolkit for accessing and analyzing
 * SEC filing data through a chainable API interface.
 */

import { EdgarClient as BaseEdgarClient } from './client/edgar-client';
import { CompanyTicker, EdgarClientConfig } from './types';
import { ItemExtractor } from './parsers/item-extractor';
import { CompanyNotFoundError, FilingContentError } from './exceptions/errors';


/**
 * Query options for filing searches
 */
export interface FilingQueryOptions {
  formTypes?: string[];
  since?: string;
  until?: string;
  limit?: number;
}

/**
 * Options for XBRL fact queries
 */
export interface FactQueryOptions {
  concept?: string;
  taxonomy?: string;
  units?: string;
  period?: string;
}

/**
 * Financial summary data
 */
export interface FinancialSummary {
  totalAssets?: number;
  totalLiabilities?: number;
  totalStockholdersEquity?: number;
  totalRevenues?: number;
}

/**
 * Key financial ratios
 */
export interface FinancialRatios {
  debtToAssets?: number;
  debtToEquity?: number;
  currentRatio?: number;
  quickRatio?: number;
  returnOnEquity?: number;
  returnOnAssets?: number;
  netProfitMargin?: number;
  grossProfitMargin?: number;
  operatingCashFlowMargin?: number;
}

/**
 * SEC EDGAR API client with fluent interface design.
 * 
 * This client provides comprehensive access to SEC filing data through
 * a chainable, type-safe API with intelligent caching and rate limiting.
 * 
 * @example
 * ```typescript
 * const client = new EdgarClient({ userAgent: "MyApp/1.0 (contact@example.com)" });
 * const company = await client.companies.lookup("AAPL");
 * const filings = await company?.filings.formTypes(["10-K"]).limit(5).fetch();
 * ```
 */
export class EdgarClient {
  private baseClient: BaseEdgarClient;
  public readonly companies: CompanyQueryBuilder;
  public readonly filings: FilingQueryBuilder;
  public readonly facts: FactsQueryBuilder;

  constructor(config: EdgarClientConfig) {
    this.baseClient = new BaseEdgarClient({ userAgent: config.userAgent });

    this.companies = new CompanyQueryBuilder(this.baseClient);
    this.filings = new FilingQueryBuilder(this.baseClient);
    this.facts = new FactsQueryBuilder(this.baseClient);
  }

  /**
   * Configure client settings with method chaining.
   */
  configure(_settings: Partial<EdgarClientConfig>): EdgarClient {
    // Could update internal settings here
    return this;
  }
}

/**
 * Fluent interface for company queries.
 */
export class CompanyQueryBuilder {
  constructor(private client: BaseEdgarClient) {}

  /**
   * Look up a single company by ticker or CIK.
   * 
   * @param identifier - Ticker symbol or CIK number
   * @returns Company object if found
   * 
   * @example
   * ```typescript
   * const company = await client.companies.lookup("AAPL");
   * ```
   */
  async lookup(identifier: string | number): Promise<Company | null> {
    try {
      let data: CompanyTicker | null = null;

      // Try as ticker first
      if (typeof identifier === 'string' && !/^\d+$/.test(identifier)) {
        data = await this.client.getCompanyByTicker(identifier);
      }

      // Try as CIK if ticker failed
      if (!data) {
        const cik = typeof identifier === 'number' 
          ? identifier.toString().padStart(10, '0')
          : identifier.padStart(10, '0');
        data = await this.client.getCompanyByCik(cik);
      }

      return data ? new Company(data, this.client) : null;
    } catch (error) {
      console.warn(`Failed to lookup company ${identifier}:`, error);
      return null;
    }
  }

  /**
   * Search for companies with fluent interface.
   * 
   * @param query - Search query
   * @returns CompanySearchBuilder for further filtering
   * 
   * @example
   * ```typescript
   * const results = await client.companies.search("Apple").limit(5).execute();
   * ```
   */
  search(query: string): CompanySearchBuilder {
    return new CompanySearchBuilder(this.client, query);
  }

  /**
   * Look up multiple companies in batch.
   * 
   * @param identifiers - List of ticker symbols or CIKs
   * @returns Array of Company objects (null for not found)
   * 
   * @example
   * ```typescript
   * const companies = await client.companies.batchLookup(["AAPL", "MSFT", "GOOGL"]);
   * ```
   */
  async batchLookup(identifiers: Array<string | number>): Promise<Array<Company | null>> {
    const promises = identifiers.map(id => this.lookup(id));
    return Promise.all(promises);
  }
}

/**
 * Builder for company search queries.
 */
export class CompanySearchBuilder {
  private _limit?: number;

  constructor(
    private client: BaseEdgarClient,
    private query: string
  ) {}

  /**
   * Limit number of results.
   */
  limit(count: number): CompanySearchBuilder {
    this._limit = count;
    return this;
  }

  /**
   * Execute the search query.
   */
  async execute(): Promise<Company[]> {
    try {
      const results = await this.client.searchCompanies(this.query);
      const companies = results.map(data => new Company(data, this.client));
      
      return this._limit ? companies.slice(0, this._limit) : companies;
    } catch (error) {
      console.warn(`Failed to search companies for "${this.query}":`, error);
      return [];
    }
  }
}

/**
 * Fluent interface for filing queries.
 */
export class FilingQueryBuilder {
  constructor(private client: BaseEdgarClient) {}

  /**
   * Get filings for a specific company.
   * 
   * @param company - Company object, ticker, or CIK
   * @returns CompanyFilingBuilder for further filtering
   * 
   * @example
   * ```typescript
   * const filings = await client.filings.forCompany("AAPL").formTypes(["10-K"]).recent(5).fetch();
   * ```
   */
  forCompany(company: Company | string | number): CompanyFilingBuilder {
    if (company instanceof Company) {
      return new CompanyFilingBuilder(this.client, company.cik);
    } else {
      // For string/number, we'll need to resolve to CIK in the builder
      return new CompanyFilingBuilder(this.client, company);
    }
  }
}

/**
 * Builder for company filing queries.
 */
export class CompanyFilingBuilder {
  private _formTypes?: string[];
  private _since?: string;
  private _until?: string;
  private _limit?: number;

  constructor(
    private client: BaseEdgarClient,
    private companyIdentifier: string | number
  ) {}

  /**
   * Filter by form types.
   */
  formTypes(forms: string[]): CompanyFilingBuilder {
    this._formTypes = forms;
    return this;
  }

  /**
   * Filter filings since date (YYYY-MM-DD).
   */
  since(date: string): CompanyFilingBuilder {
    this._since = date;
    return this;
  }

  /**
   * Filter filings until date (YYYY-MM-DD).
   */
  until(date: string): CompanyFilingBuilder {
    this._until = date;
    return this;
  }

  /**
   * Limit to most recent filings.
   */
  recent(count: number): CompanyFilingBuilder {
    this._limit = count;
    return this;
  }

  /**
   * Execute the query and fetch filings.
   */
  async fetch(): Promise<Filing[]> {
    try {
      // Resolve CIK if needed
      let cik: string;
      if (typeof this.companyIdentifier === 'string' && this.companyIdentifier.length === 10) {
        cik = this.companyIdentifier;
      } else {
        const company = await new CompanyQueryBuilder(this.client).lookup(this.companyIdentifier);
        if (!company) {
          throw new CompanyNotFoundError(
            this.companyIdentifier,
            typeof this.companyIdentifier === 'string' && this.companyIdentifier.length === 10 ? 'cik' : 
            typeof this.companyIdentifier === 'number' ? 'cik' : 'ticker'
          );
        }
        cik = company.cik;
      }

      // Get submissions
      const submissions = await this.client.getCompanySubmissions(cik);

      const filings: Filing[] = [];
      const recentFilings = submissions.filings?.recent;

      if (recentFilings) {
        const { accessionNumber = [], form = [], filingDate = [] } = recentFilings;

        for (let i = 0; i < accessionNumber.length; i++) {
          if (i >= form.length || i >= filingDate.length) break;

          const formType = form[i];
          const date = filingDate[i];

          // Filter by form types if specified
          if (this._formTypes && !this._formTypes.includes(formType)) {
            continue;
          }

          const filingData = {
            cik,
            accessionNumber: accessionNumber[i],
            formType,
            filingDate: date,
          };

          const filing = new Filing(filingData, this.client);
          filings.push(filing);

          if (this._limit && filings.length >= this._limit) {
            break;
          }
        }
      }

      return filings;
    } catch (error) {
      console.warn('Failed to fetch filings:', error);
      return [];
    }
  }
}

/**
 * Fluent interface for XBRL facts queries.
 */
export class FactsQueryBuilder {
  constructor(private client: BaseEdgarClient) {}

  /**
   * Get facts for a specific company.
   * 
   * @param company - Company object, ticker, or CIK
   * @returns CompanyFactsBuilder for further querying
   * 
   * @example
   * ```typescript
   * const facts = await client.facts.forCompany("AAPL").concept("Assets").inUnits("USD").fetch();
   * ```
   */
  forCompany(company: Company | string | number): CompanyFactsBuilder {
    if (company instanceof Company) {
      return new CompanyFactsBuilder(this.client, company.cik);
    } else {
      return new CompanyFactsBuilder(this.client, company);
    }
  }
}

/**
 * Builder for company facts queries.
 */
export class CompanyFactsBuilder {
  private _concept?: string;
  private _taxonomy: string = 'us-gaap';
  private _units?: string;
  private _period?: string;

  constructor(
    private client: BaseEdgarClient,
    private companyIdentifier: string | number
  ) {}

  /**
   * Filter by specific concept.
   */
  concept(conceptName: string): CompanyFactsBuilder {
    this._concept = conceptName;
    return this;
  }

  /**
   * Specify taxonomy (default: us-gaap).
   */
  taxonomy(taxonomyName: string): CompanyFactsBuilder {
    this._taxonomy = taxonomyName;
    return this;
  }

  /**
   * Filter by units (e.g., USD, shares).
   */
  inUnits(units: string): CompanyFactsBuilder {
    this._units = units;
    return this;
  }

  /**
   * Filter by period.
   */
  period(periodFilter: string): CompanyFactsBuilder {
    this._period = periodFilter;
    return this;
  }

  /**
   * Execute the query and fetch facts.
   */
  async fetch(): Promise<Array<Record<string, any>>> {
    try {
      // Resolve CIK if needed
      let cik: string;
      if (typeof this.companyIdentifier === 'string' && this.companyIdentifier.length === 10) {
        cik = this.companyIdentifier;
      } else {
        const company = await new CompanyQueryBuilder(this.client).lookup(this.companyIdentifier);
        if (!company) {
          throw new CompanyNotFoundError(
            this.companyIdentifier,
            typeof this.companyIdentifier === 'string' && this.companyIdentifier.length === 10 ? 'cik' : 
            typeof this.companyIdentifier === 'number' ? 'cik' : 'ticker'
          );
        }
        cik = company.cik;
      }

      if (this._concept) {
        const data = await this.client.getCompanyConcept(cik, this._taxonomy, this._concept, this._units);
        return this.processConceptData(data);
      } else {
        const facts = await this.client.getCompanyFacts(cik);
        return this.processAllFacts(facts);
      }
    } catch (error) {
      console.warn('Failed to fetch facts:', error);
      return [];
    }
  }

  private processConceptData(data: Record<string, any>): Array<Record<string, any>> {
    const results: Array<Record<string, any>> = [];
    const units = data.units || {};

    for (const [unit, unitData] of Object.entries(units)) {
      if (this._units && unit !== this._units) continue;

      if (Array.isArray(unitData)) {
        for (const fact of unitData) {
          if (this._period) {
            const factPeriod = fact.fy || fact.fp || fact.frame || '';
            if (!factPeriod.toString().includes(this._period)) continue;
          }

          const factRecord = {
            concept: this._concept,
            value: fact.val,
            unit,
            period: fact.frame || `FY${fact.fy || ''}${fact.fp || ''}`,
            fiscalYear: fact.fy,
            fiscalPeriod: fact.fp,
            filed: fact.filed,
            form: fact.form,
          };
          results.push(factRecord);
        }
      }
    }

    return results;
  }

  private processAllFacts(facts: Record<string, any>): Array<Record<string, any>> {
    const results: Array<Record<string, any>> = [];
    
    // Process us-gaap facts
    if (facts['us-gaap']) {
      for (const [concept, conceptData] of Object.entries(facts['us-gaap'])) {
        if (conceptData && typeof conceptData === 'object' && 'units' in conceptData) {
          const units = conceptData.units;
          
          for (const [unit, unitData] of Object.entries(units as Record<string, any>)) {
            if (Array.isArray(unitData)) {
              for (const fact of unitData) {
                results.push({
                  concept,
                  taxonomy: 'us-gaap',
                  unit,
                  value: fact.val,
                  period: fact.period,
                  form: fact.form,
                  frame: fact.frame,
                  accn: fact.accn,
                });
              }
            }
          }
        }
      }
    }
    
    // Process dei facts  
    if (facts.dei) {
      for (const [concept, conceptData] of Object.entries(facts.dei)) {
        if (conceptData && typeof conceptData === 'object' && 'units' in conceptData) {
          const units = conceptData.units;
          
          for (const [unit, unitData] of Object.entries(units as Record<string, any>)) {
            if (Array.isArray(unitData)) {
              for (const fact of unitData) {
                results.push({
                  concept,
                  taxonomy: 'dei',
                  unit,
                  value: fact.val,
                  period: fact.period,
                  form: fact.form,
                  frame: fact.frame,
                  accn: fact.accn,
                });
              }
            }
          }
        }
      }
    }
    
    return results;
  }
}

/**
 * Comprehensive company representation with fluent interface design.
 * 
 * This class provides rich access to company data, filings, and financial
 * information through an intuitive, chainable API.
 */
export class Company {
  public readonly cik: string;
  public readonly ticker: string;
  public readonly name: string;
  public readonly exchange: string;

  constructor(
    private data: CompanyTicker,
    private client: BaseEdgarClient
  ) {
    this.cik = data.cik_str;
    this.ticker = data.ticker || '';
    this.name = data.title;
    this.exchange = data.exchange || '';
  }

  /**
   * Get filings builder for this company.
   */
  get filings(): CompanyFilingBuilder {
    return new CompanyFilingBuilder(this.client, this.cik);
  }

  /**
   * Get facts builder for this company.
   */
  get facts(): CompanyFactsBuilder {
    return new CompanyFactsBuilder(this.client, this.cik);
  }

  /**
   * Get the most recent filing of a specific type.
   * 
   * @param formType - Type of form to retrieve
   * @returns Most recent filing or null
   * 
   * @example
   * ```typescript
   * const latest10K = await company.getLatestFiling("10-K");
   * ```
   */
  async getLatestFiling(formType: string = '10-K'): Promise<Filing | null> {
    const filings = await this.filings.formTypes([formType]).recent(1).fetch();
    return filings[0] || null;
  }

  /**
   * Get a summary of key financial metrics.
   * 
   * @returns Object with key financial data
   * 
   * @example
   * ```typescript
   * const summary = await company.getFinancialSummary();
   * console.log(`Assets: $${summary.totalAssets?.toLocaleString()}`);
   * ```
   */
  async getFinancialSummary(): Promise<FinancialSummary> {
    const keyConcepts = ['Assets', 'Liabilities', 'StockholdersEquity', 'Revenues'];
    const summary: FinancialSummary = {};

    for (const concept of keyConcepts) {
      try {
        const facts = await this.facts.concept(concept).inUnits('USD').fetch();
        if (facts.length > 0) {
          const latest = facts.reduce((latest, fact) => 
            (fact.filed > latest.filed) ? fact : latest
          );
          const key = `total${concept}` as keyof FinancialSummary;
          (summary as any)[key] = latest.value;
        }
      } catch (error) {
        console.warn(`Failed to get ${concept}:`, error);
      }
    }

    return summary;
  }

  toString(): string {
    return this.ticker ? `${this.ticker}: ${this.name}` : `CIK ${this.cik}: ${this.name}`;
  }
}

/**
 * Comprehensive filing representation with advanced content processing.
 * 
 * This class provides rich access to SEC filing content, structured data
 * extraction, and financial analysis capabilities.
 */
export class Filing {
  public readonly cik: string;
  public readonly accessionNumber: string;
  public readonly formType: string;
  public readonly filingDate: string;
  private extractedItems: Record<string, string> | null = null;
  private itemExtractor = new ItemExtractor();

  constructor(
    private data: Record<string, any>,
    private client: BaseEdgarClient
  ) {
    this.cik = data.cik;
    this.accessionNumber = data.accessionNumber;
    this.formType = data.formType;
    this.filingDate = data.filingDate;
  }

  /**
   * Get content access interface.
   */
  get content(): FilingContentAccess {
    return new FilingContentAccess(this);
  }

  /**
   * Get analysis interface.
   */
  get analysis(): FilingAnalysis {
    return new FilingAnalysis(this);
  }

  /**
   * Get XBRL instance for this filing.
   * 
   * @returns XBRLInstance for accessing XBRL data
   * 
   * @example
   * ```typescript
   * const xbrl = await filing.xbrl();
   * const assets = await xbrl.getConceptValue("Assets");
   * ```
   */
  async xbrl(): Promise<any> {
    const { XBRLInstance } = await import('./core/xbrl');
    return new XBRLInstance(this, this.client as any);
  }

  /**
   * Get API access for internal use
   */
  get api(): any {
    return this.client;
  }

  /**
   * Get a preview of the filing content.
   * 
   * @param length - Number of characters to preview
   * @returns Preview text
   */
  async preview(length: number = 500): Promise<string> {
    try {
      const text = await this.content.asText();
      return text.length > length ? text.substring(0, length) + '...' : text;
    } catch (error) {
      return 'Content preview not available';
    }
  }

  /**
   * Extract individual items from the filing (e.g., Item 1, Item 1A, etc.).
   * 
   * @param itemNumbers - Optional list of specific item numbers to extract.
   *                     If not provided, extracts all items.
   * @returns Dictionary mapping item numbers to their content
   * 
   * @example
   * const filing = await company.getFiling("10-K");
   * const items = await filing.extractItems();
   * console.log(items["1"]);  // Business section
   * console.log(items["1A"]); // Risk Factors
   * 
   * // Extract specific items only
   * const specificItems = await filing.extractItems(["1", "1A", "7"]);
   */
  async extractItems(itemNumbers?: string[]): Promise<Record<string, string>> {
    if (!this.extractedItems) {
      // Get the filing content
      const content = await this.content.asText();
      
      // Extract all items
      try {
        this.extractedItems = this.itemExtractor.extractItems(content, this.formType);
      } catch (error) {
        console.warn(`Item extraction not supported for ${this.formType}: ${error}`);
        this.extractedItems = {};
      }
    }
    
    if (itemNumbers) {
      // Return only requested items
      const result: Record<string, string> = {};
      for (const itemNum of itemNumbers) {
        if (itemNum in this.extractedItems) {
          result[itemNum] = this.extractedItems[itemNum];
        }
      }
      return result;
    } else {
      return this.extractedItems;
    }
  }

  /**
   * Get a specific item from the filing.
   * 
   * @param itemNumber - The item number to retrieve (e.g., "1", "1A", "7")
   * @returns The item content or undefined if not found
   * 
   * @example
   * const filing = await company.getFiling("10-K");
   * const riskFactors = await filing.getItem("1A");
   * const business = await filing.getItem("1");
   */
  async getItem(itemNumber: string): Promise<string | undefined> {
    const items = await this.extractItems([itemNumber]);
    return items[itemNumber];
  }

  /**
   * Get all extracted items from the filing.
   * 
   * This is a convenience property that extracts all items.
   * 
   * @returns Dictionary mapping item numbers to their content
   * 
   * @example
   * const filing = await company.getFiling("10-K");
   * const allItems = await filing.items;
   * for (const [itemNum, content] of Object.entries(allItems)) {
   *   console.log(`Item ${itemNum}: ${content.length} characters`);
   * }
   */
  get items(): Promise<Record<string, string>> {
    return this.extractItems();
  }

  toString(): string {
    return `${this.formType} filing for ${this.cik} on ${this.filingDate}`;
  }
}

/**
 * Interface for accessing filing content.
 */
export class FilingContentAccess {
  constructor(private filing: Filing) {}

  /**
   * Get filing as plain text.
   */
  async asText(clean: boolean = true): Promise<string> {
    try {
      const api = this.filing.api as any;
      const details = await api.getFiling(this.filing.cik, this.filing.accessionNumber);
      
      // Find the main document URL
      const accessionClean = this.filing.accessionNumber.replace(/-/g, '');
      let mainDocument: string | null = null;
      
      if (details?.directory?.item) {
        const items = Array.isArray(details.directory.item) ? details.directory.item : [details.directory.item];
        
        for (const item of items) {
          const name = item.name || '';
          if ((name.endsWith('.htm') || name.endsWith('.txt')) && !name.endsWith('-index.htm')) {
            if (name.includes(this.filing.formType.toLowerCase()) || name.includes('filing')) {
              mainDocument = name;
              break;
            } else if (!mainDocument) {
              mainDocument = name;
            }
          }
        }
      }
      
      if (!mainDocument) {
        // Fallback to common naming patterns
        mainDocument = `${this.filing.accessionNumber}.txt`;
      }
      
      // Construct document URL
      const documentUrl = `https://www.sec.gov/Archives/edgar/data/${this.filing.cik}/${accessionClean}/${mainDocument}`;
      
      // Fetch content
      const response = await fetch(documentUrl);
      if (!response.ok) {
        throw new FilingContentError(
          `Failed to fetch filing content: ${response.status} ${response.statusText}`,
          this.filing.accessionNumber,
          'text/html'
        );
      }
      
      let content = await response.text();
      
      if (clean) {
        // Remove HTML/SGML tags
        content = content.replace(/<[^>]+>/g, ' ');
        // Clean up whitespace
        content = content.replace(/\s+/g, ' ').trim();
      }
      
      return content;
    } catch (error) {
      throw new FilingContentError(
          `Failed to fetch filing text: ${error}`,
          this.filing.accessionNumber,
          'text/plain'
        );
    }
  }

  /**
   * Get filing as HTML.
   */
  async asHtml(): Promise<string> {
    // Get raw content without cleaning
    return this.asText(false);
  }

  /**
   * Get filing as structured data.
   */
  async asStructuredData(): Promise<Record<string, any>> {
    const content = await this.asText();
    const structuredData: Record<string, any> = {
      formType: this.filing.formType,
      filingDate: this.filing.filingDate,
      accessionNumber: this.filing.accessionNumber,
      cik: this.filing.cik,
    };
    
    // Extract basic metadata
    const companyMatch = content.match(/COMPANY\s+(?:CONFORMED\s+)?NAME:\s*([^\n]+)/i);
    if (companyMatch) {
      structuredData.companyName = companyMatch[1].trim();
    }
    
    const periodMatch = content.match(/CONFORMED\s+PERIOD\s+OF\s+REPORT:\s*(\d{8})/i);
    if (periodMatch) {
      structuredData.periodOfReport = periodMatch[1];
    }
    
    // Form-specific parsing
    if (this.filing.formType === '8-K') {
      const events: Record<string, string> = {};
      const itemPatterns = [
        ['1.01', /Item\s+1\.01[^a-zA-Z]*([^\n\r]+)/i],
        ['2.02', /Item\s+2\.02[^a-zA-Z]*([^\n\r]+)/i],
        ['3.02', /Item\s+3\.02[^a-zA-Z]*([^\n\r]+)/i],
        ['5.02', /Item\s+5\.02[^a-zA-Z]*([^\n\r]+)/i],
        ['7.01', /Item\s+7\.01[^a-zA-Z]*([^\n\r]+)/i],
        ['8.01', /Item\s+8\.01[^a-zA-Z]*([^\n\r]+)/i],
      ];
      
      for (const [item, pattern] of itemPatterns) {
        const match = content.match(pattern as RegExp);
        if (match) {
          events[item as string] = match[1].trim();
        }
      }
      
      if (Object.keys(events).length > 0) {
        structuredData.currentEvents = events;
      }
    }
    
    return structuredData;
  }

  /**
   * Get direct download URL.
   */
  getDownloadUrl(): string {
    const accessionClean = this.filing.accessionNumber.replace(/-/g, '');
    return `https://www.sec.gov/Archives/edgar/data/${this.filing.cik}/${accessionClean}/${this.filing.accessionNumber}-index.htm`;
  }
}

/**
 * Interface for filing analysis and extraction.
 */
export class FilingAnalysis {
  constructor(private filing: Filing) {}

  /**
   * Extract financial data if available.
   */
  async extractFinancials(): Promise<FinancialData | null> {
    if (['10-K', '10-Q'].includes(this.filing.formType)) {
      return new FinancialData(this.filing);
    }
    return null;
  }

  /**
   * Extract key business metrics.
   */
  async extractKeyMetrics(): Promise<Record<string, any>> {
    try {
      const structured = await this.filing.content.asStructuredData();
      
      if (this.filing.formType === '8-K') {
        return structured.currentEvents || {};
      } else if (['3', '4', '5'].includes(this.filing.formType)) {
        return {
          insiderTransactions: structured.nonDerivativeTransactions?.length || 0,
          holdings: structured.nonDerivativeHoldings?.length || 0,
        };
      }
      
      return {};
    } catch (error) {
      return {};
    }
  }
}

/**
 * Enhanced financial data interface.
 */
export class FinancialData {
  constructor(private filing: Filing) {}

  /**
   * Get balance sheet data.
   */
  async getBalanceSheet(): Promise<Record<string, any> | null> {
    try {
      const xbrl = await this.filing.xbrl();
      
      const balanceSheet: Record<string, any> = {
        assets: {
          current: await xbrl.getConceptValue('AssetsCurrent'),
          nonCurrent: await xbrl.getConceptValue('AssetsNoncurrent'),
          total: await xbrl.getConceptValue('Assets'),
        },
        liabilities: {
          current: await xbrl.getConceptValue('LiabilitiesCurrent'),
          nonCurrent: await xbrl.getConceptValue('LiabilitiesNoncurrent'),
          total: await xbrl.getConceptValue('Liabilities'),
        },
        equity: {
          total: await xbrl.getConceptValue('StockholdersEquity'),
          retainedEarnings: await xbrl.getConceptValue('RetainedEarningsAccumulatedDeficit'),
        },
      };
      
      // Only return if we have some data
      if (balanceSheet.assets.total || balanceSheet.liabilities.total) {
        return balanceSheet;
      }
      
      return null;
    } catch (error) {
      console.warn('Failed to extract balance sheet:', error);
      return null;
    }
  }

  /**
   * Get income statement data.
   */
  async getIncomeStatement(): Promise<Record<string, any> | null> {
    try {
      const xbrl = await this.filing.xbrl();
      
      const incomeStatement: Record<string, any> = {
        revenue: await xbrl.getConceptValue('Revenues'),
        costOfRevenue: await xbrl.getConceptValue('CostOfRevenue'),
        grossProfit: await xbrl.getConceptValue('GrossProfit'),
        operatingExpenses: {
          total: await xbrl.getConceptValue('OperatingExpenses'),
          rd: await xbrl.getConceptValue('ResearchAndDevelopmentExpense'),
          sga: await xbrl.getConceptValue('SellingGeneralAndAdministrativeExpense'),
        },
        operatingIncome: await xbrl.getConceptValue('OperatingIncomeLoss'),
        netIncome: await xbrl.getConceptValue('NetIncomeLoss'),
        eps: {
          basic: await xbrl.getConceptValue('EarningsPerShareBasic'),
          diluted: await xbrl.getConceptValue('EarningsPerShareDiluted'),
        },
      };
      
      // Only return if we have some data
      if (incomeStatement.revenue || incomeStatement.netIncome) {
        return incomeStatement;
      }
      
      return null;
    } catch (error) {
      console.warn('Failed to extract income statement:', error);
      return null;
    }
  }

  /**
   * Get cash flow statement data.
   */
  async getCashFlow(): Promise<Record<string, any> | null> {
    try {
      const xbrl = await this.filing.xbrl();
      
      const cashFlow: Record<string, any> = {
        operating: {
          netCashFlow: await xbrl.getConceptValue('NetCashProvidedByUsedInOperatingActivities'),
          netIncome: await xbrl.getConceptValue('NetIncomeLoss'),
          depreciation: await xbrl.getConceptValue('DepreciationDepletionAndAmortization'),
        },
        investing: {
          netCashFlow: await xbrl.getConceptValue('NetCashProvidedByUsedInInvestingActivities'),
          capitalExpenditures: await xbrl.getConceptValue('PaymentsToAcquirePropertyPlantAndEquipment'),
        },
        financing: {
          netCashFlow: await xbrl.getConceptValue('NetCashProvidedByUsedInFinancingActivities'),
          dividends: await xbrl.getConceptValue('PaymentsOfDividends'),
          stockRepurchases: await xbrl.getConceptValue('PaymentsForRepurchaseOfCommonStock'),
        },
        netChange: await xbrl.getConceptValue('CashAndCashEquivalentsPeriodIncreaseDecrease'),
        endingCash: await xbrl.getConceptValue('CashAndCashEquivalentsAtCarryingValue'),
      };
      
      // Only return if we have some data
      if (cashFlow.operating.netCashFlow || cashFlow.netChange) {
        return cashFlow;
      }
      
      return null;
    } catch (error) {
      console.warn('Failed to extract cash flow:', error);
      return null;
    }
  }

  /**
   * Calculate key financial ratios.
   */
  async getKeyRatios(): Promise<FinancialRatios> {
    const ratios: FinancialRatios = {};
    
    try {
      const [balanceSheet, incomeStatement, cashFlow] = await Promise.all([
        this.getBalanceSheet(),
        this.getIncomeStatement(),
        this.getCashFlow(),
      ]);
      
      if (balanceSheet && incomeStatement) {
        // Profitability ratios
        if (incomeStatement.netIncome && incomeStatement.revenue) {
          ratios.netProfitMargin = incomeStatement.netIncome / incomeStatement.revenue;
        }
        
        if (incomeStatement.grossProfit && incomeStatement.revenue) {
          ratios.grossProfitMargin = incomeStatement.grossProfit / incomeStatement.revenue;
        }
        
        // Return ratios
        if (incomeStatement.netIncome && balanceSheet.equity?.total) {
          ratios.returnOnEquity = incomeStatement.netIncome / balanceSheet.equity.total;
        }
        
        if (incomeStatement.netIncome && balanceSheet.assets?.total) {
          ratios.returnOnAssets = incomeStatement.netIncome / balanceSheet.assets.total;
        }
        
        // Liquidity ratios
        if (balanceSheet.assets?.current && balanceSheet.liabilities?.current) {
          ratios.currentRatio = balanceSheet.assets.current / balanceSheet.liabilities.current;
          
          // Quick ratio (approximate - would need inventory data)
          ratios.quickRatio = balanceSheet.assets.current * 0.8 / balanceSheet.liabilities.current;
        }
        
        // Leverage ratios
        if (balanceSheet.liabilities?.total && balanceSheet.equity?.total) {
          ratios.debtToEquity = balanceSheet.liabilities.total / balanceSheet.equity.total;
        }
      }
      
      if (cashFlow && incomeStatement) {
        // Cash flow ratios
        if (cashFlow.operating?.netCashFlow && incomeStatement.revenue) {
          ratios.operatingCashFlowMargin = cashFlow.operating.netCashFlow / incomeStatement.revenue;
        }
      }
    } catch (error) {
      console.warn('Failed to calculate ratios:', error);
    }
    
    return ratios;
  }
}

// Convenience functions
export function createClient(config: EdgarClientConfig): EdgarClient {
  /**
   * Create an Edgar client instance.
   * 
   * @param config - Client configuration
   * @returns EdgarClient instance
   * 
   * @example
   * ```typescript
   * const client = createClient({ userAgent: "MyApp/1.0 (contact@example.com)" });
   * ```
   */
  return new EdgarClient(config);
}

