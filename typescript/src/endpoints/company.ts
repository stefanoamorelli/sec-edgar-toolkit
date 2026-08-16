/**
 * Company endpoints for SEC EDGAR API
 */

import { HttpClient } from "../utils";
import { CompanyTicker } from "../types";

// The ticker mapping file is served from www.sec.gov, not data.sec.gov
const SEC_FILES_URL = "https://www.sec.gov";

export class CompanyEndpoints {
  private httpClient: HttpClient;
  private companyTickersCache: Record<string, any> | null = null;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  async getCompanyTickers(
    forceRefresh: boolean = false,
  ): Promise<Record<string, any>> {
    if (!this.companyTickersCache || forceRefresh) {
      const url = `${SEC_FILES_URL}/files/company_tickers.json`;
      this.companyTickersCache = await this.httpClient.get(url);
    }
    return this.companyTickersCache!;
  }

  /** Normalize a raw ticker-file entry (cik_str arrives as a number). */
  private static normalizeEntry(company: Record<string, any>): CompanyTicker {
    return {
      ...company,
      cik_str: String(company.cik_str).padStart(10, "0"),
    } as CompanyTicker;
  }

  async getCompanyByTicker(ticker: string): Promise<CompanyTicker | null> {
    const tickers = await this.getCompanyTickers();
    const upperTicker = ticker.toUpperCase();

    for (const [, company] of Object.entries(tickers)) {
      if (
        typeof company === "object" &&
        company !== null &&
        "ticker" in company
      ) {
        if (company.ticker?.toUpperCase() === upperTicker) {
          return CompanyEndpoints.normalizeEntry(company);
        }
      }
    }

    return null;
  }

  async getCompanyByCik(cik: string | number): Promise<CompanyTicker | null> {
    const tickers = await this.getCompanyTickers();
    const cikNumeric = parseInt(String(cik), 10);

    for (const [, company] of Object.entries(tickers)) {
      if (
        typeof company === "object" &&
        company !== null &&
        "cik_str" in company
      ) {
        if (parseInt(String(company.cik_str), 10) === cikNumeric) {
          return CompanyEndpoints.normalizeEntry(company);
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
      if (
        typeof company === "object" &&
        company !== null &&
        "title" in company
      ) {
        if (
          company.title?.toLowerCase().includes(lowerQuery) ||
          company.ticker?.toLowerCase().includes(lowerQuery)
        ) {
          results.push(CompanyEndpoints.normalizeEntry(company));
        }
      }
    }

    return results;
  }
}
