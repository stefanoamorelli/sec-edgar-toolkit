/**
 * Company-related type definitions
 */

export interface CompanyTicker {
  cik_str: string;
  ticker: string;
  title: string;
  exchange?: string;
}

export interface CompanySubmissions {
  cik: string;
  entityType: string;
  sic?: string;
  sicDescription?: string;
  insiderTransactionForOwnerExists: boolean;
  insiderTransactionForIssuerExists: boolean;
  name: string;
  tickers: string[];
  exchanges: string[];
  ein?: string;
  description?: string;
  website?: string;
  investorWebsite?: string;
  category?: string;
  fiscalYearEnd?: string;
  stateOfIncorporation?: string;
  stateOfIncorporationDescription?: string;
  addresses: Record<string, any>;
  phone?: string;
  flags?: string;
  formerNames: Array<Record<string, string>>;
  filings: Record<string, any>;
}