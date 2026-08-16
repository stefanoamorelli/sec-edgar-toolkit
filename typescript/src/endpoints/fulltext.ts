/**
 * Full-text search endpoints (EDGAR full-text search, efts.sec.gov).
 *
 * Searches the text of filings themselves, not just metadata, covering
 * filings from 2001 onward. Supports exact phrases (quote the query),
 * form-type filters, date ranges, and company filters.
 */

import { HttpClient } from "../utils";

const SEARCH_URL = "https://efts.sec.gov/LATEST/search-index";

export interface FullTextHit {
  accessionNumber: string;
  document: string;
  cik: string;
  companyName: string;
  formType: string;
  rootForms: string[];
  filingDate: string;
  periodEnding: string;
  fileType: string;
  fileDescription: string;
  score: number | null;
}

export interface FullTextSearchResults {
  total: number;
  hits: FullTextHit[];
}

export interface FullTextSearchOptions {
  forms?: string | string[];
  startDate?: string;
  endDate?: string;
  cik?: string | number;
  offset?: number;
}

export class FullTextSearchEndpoints {
  private httpClient: HttpClient;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  /**
   * Search the full text of filings.
   *
   * @param query Search terms; quote a phrase for exact matching
   * @param options Form, date-range, company, and paging filters
   */
  async search(
    query: string,
    options: FullTextSearchOptions = {},
  ): Promise<FullTextSearchResults> {
    const params = new URLSearchParams({ q: query });
    if (options.forms) {
      const forms = Array.isArray(options.forms)
        ? options.forms
        : [options.forms];
      params.set("forms", forms.join(","));
    }
    if (options.startDate || options.endDate) {
      params.set("dateRange", "custom");
      if (options.startDate) {
        params.set("startdt", options.startDate);
      }
      if (options.endDate) {
        params.set("enddt", options.endDate);
      }
    }
    if (options.cik !== undefined) {
      params.set("ciks", String(options.cik).padStart(10, "0"));
    }
    if (options.offset) {
      params.set("from", String(options.offset));
    }

    const data = await this.httpClient.get(
      `${SEARCH_URL}?${params.toString()}`,
    );

    const rawHits = data?.hits || {};
    const total = rawHits?.total?.value || 0;

    const hits: FullTextHit[] = [];
    for (const entry of rawHits?.hits || []) {
      const source = entry?._source || {};
      const id = String(entry?._id || "");
      const separator = id.indexOf(":");
      const accession = separator >= 0 ? id.slice(0, separator) : id;
      const document = separator >= 0 ? id.slice(separator + 1) : "";
      const ciks: string[] = source.ciks || [];
      const displayNames: string[] = source.display_names || [];

      hits.push({
        accessionNumber: accession,
        document,
        cik:
          ciks.length > 0 ? ciks[0].replace(/^0+/, "").padStart(10, "0") : "",
        companyName:
          displayNames.length > 0 ? displayNames[0].split("  (CIK")[0] : "",
        formType: source.form || "",
        rootForms: source.root_forms || [],
        filingDate: source.file_date || "",
        periodEnding: source.period_ending || "",
        fileType: source.file_type || "",
        fileDescription: source.file_description || "",
        score: entry?._score ?? null,
      });
    }

    return { total, hits };
  }
}
