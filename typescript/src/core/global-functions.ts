/**
 * Module-level entry points of the object API.
 *
 * Identity setup, company lookup and search, and filing retrieval.
 */

import { EdgarClient } from "../client/edgar-client";
import { Filings } from "./collections";
import { Company } from "./company";
import { Filing } from "./filing";

let globalApi: EdgarClient | null = null;

/**
 * Set the user agent for SEC API requests.
 *
 * @example
 * setIdentity("MyCompany/1.0 (contact@example.com)")
 */
export function setIdentity(userAgent: string): void {
  globalApi = new EdgarClient({ userAgent });
}

/** Get the global API instance, creating one from the environment if needed. */
export function getApi(): EdgarClient {
  if (globalApi === null) {
    // EdgarClient falls back to SEC_EDGAR_TOOLKIT_USER_AGENT and throws
    // a descriptive error when no identity is available.
    globalApi = new EdgarClient();
  }
  return globalApi;
}

/**
 * Find a company by ticker or CIK.
 *
 * @returns Company, or null when the identifier cannot be resolved
 */
export async function findCompany(
  identifier: string | number,
): Promise<Company | null> {
  try {
    return await Company.lookup(identifier, getApi());
  } catch {
    return null;
  }
}

/** Search for companies by name. */
export async function search(query: string): Promise<Company[]> {
  const api = getApi();
  const results = await api.searchCompanies(query);
  const companies: Company[] = [];
  for (const result of results) {
    const company = await findCompany(result.cik_str);
    if (company) {
      companies.push(company);
    }
  }
  return companies;
}

export interface GlobalGetFilingsOptions {
  form?: string | string[];
  cik?: string | number;
  ticker?: string;
  since?: string;
  before?: string;
  limit?: number;
}

/** Get filings with flexible filtering options. */
export async function getFilings(
  options: GlobalGetFilingsOptions = {},
): Promise<Filings> {
  const { form, cik, ticker, since, before, limit } = options;

  if (ticker || cik != null) {
    const company = await findCompany(ticker || cik!);
    if (!company) {
      return new Filings();
    }
    return company.getFilings({ form, since, before, limit });
  }

  return getCurrentFilings(form, limit || 40);
}

/**
 * Get the most recent filings across all companies (near real-time feed).
 *
 * @param form Form type(s) to filter by (e.g., "8-K", ["3", "4", "5"])
 * @param pageSize Maximum number of filings to return
 * @param owner Ownership-filing filter: "include", "exclude", or "only"
 */
export async function getCurrentFilings(
  form?: string | string[],
  pageSize: number = 40,
  owner: "include" | "exclude" | "only" = "include",
): Promise<Filings> {
  const api = getApi();
  const entries = await api.filings.getRecentFilings(form, pageSize, owner);

  const filings = new Filings();
  for (const entry of entries) {
    filings.push(
      new Filing({
        cik: entry.cik || "0",
        accessionNumber: entry.accessionNumber,
        formType: entry.formType,
        filingDate: entry.filingDate,
        api,
        companyName: entry.companyName,
      }),
    );
    if (filings.length >= pageSize) {
      break;
    }
  }
  return filings;
}
