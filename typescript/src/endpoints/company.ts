/**
 * Company endpoints for SEC EDGAR API
 */

import { HttpClient } from '../utils';
import { CompanyTicker } from '../types';

const SEC_BASE_URL = 'https://data.sec.gov';

export class CompanyEndpoints {
  private httpClient: HttpClient;
  private companyTickersCache: Record<string, any> | null = null;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  async getCompanyTickers(forceRefresh: boolean = false): Promise<Record<string, any>> {
    if (!this.companyTickersCache || forceRefresh) {
      const url = `${SEC_BASE_URL}/files/company_tickers.json`;
      this.companyTickersCache = await this.httpClient.get(url);
    }
    return this.companyTickersCache!;
  }

  async getCompanyByTicker(ticker: string): Promise<CompanyTicker | null> {
    const tickers = await this.getCompanyTickers();
    const upperTicker = ticker.toUpperCase();
    
    for (const [, company] of Object.entries(tickers)) {
      if (typeof company === 'object' && company !== null && 'ticker' in company) {
        if (company.ticker?.toUpperCase() === upperTicker) {
          return company as CompanyTicker;
        }
      }
    }
    
    return null;
  }

  async getCompanyByCik(cik: string | number): Promise<CompanyTicker | null> {
    const tickers = await this.getCompanyTickers();
    const cikStr = typeof cik === 'number' ? cik.toString().padStart(10, '0') : cik.padStart(10, '0');
    
    for (const [, company] of Object.entries(tickers)) {
      if (typeof company === 'object' && company !== null && 'cik_str' in company) {
        if (company.cik_str === cikStr) {
          return company as CompanyTicker;
        }
      }
    }
    
    return null;
  }

  async searchCompanies(query: string): Promise<CompanyTicker[]> {
    const tickers = await this.getCompanyTickers();
    const lowerQuery = query.toLowerCase();
    const results: CompanyTicker[] = [];
    
    for (const [, company] of Object.entries(tickers)) {
      if (typeof company === 'object' && company !== null && 'title' in company) {
        const companyData = company as CompanyTicker;
        if (companyData.title?.toLowerCase().includes(lowerQuery) ||
            companyData.ticker?.toLowerCase().includes(lowerQuery)) {
          results.push(companyData);
        }
      }
    }
    
    return results;
  }
}