/**
 * Filing endpoints for SEC EDGAR API
 */

import { HttpClient } from "../utils";
import { CompanySubmissions, RequestOptions } from "../types";

const SEC_BASE_URL = "https://data.sec.gov";
const SEC_ARCHIVES_URL = "https://www.sec.gov";
const SEC_CURRENT_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar";

export interface RecentFilingEntry {
  cik: string;
  accessionNumber: string;
  formType: string;
  filingDate: string;
  companyName: string;
  url: string;
}

export class FilingsEndpoints {
  private httpClient: HttpClient;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  async getCompanySubmissions(
    cik: string | number,
    options: RequestOptions = {},
  ): Promise<CompanySubmissions> {
    const cikStr =
      typeof cik === "number"
        ? cik.toString().padStart(10, "0")
        : cik.padStart(10, "0");
    const url = `${SEC_BASE_URL}/submissions/CIK${cikStr}.json`;

    let submissions = await this.httpClient.get(url);

    // Apply filters if provided
    if (options.submissionType || options.fromDate || options.toDate) {
      submissions = this.filterSubmissions(submissions, options);
    }

    return submissions;
  }

  async getFiling(
    cik: string | number,
    accessionNumber: string,
  ): Promise<Record<string, any>> {
    // Archive folders live on www.sec.gov, use the unpadded CIK, and the
    // folder listing is served as index.json
    const cikStr = typeof cik === "number" ? cik.toString() : cik;
    const accessionFormatted = accessionNumber.replace(/-/g, "");
    const url = `${SEC_ARCHIVES_URL}/Archives/edgar/data/${parseInt(cikStr, 10)}/${accessionFormatted}/index.json`;

    return await this.httpClient.get(url);
  }

  /**
   * Fetch one older-history submissions page (from `filings.files`).
   *
   * The main submissions payload lists additional filing history in
   * `filings.files` (e.g. `CIK0000320193-submissions-001.json`); this
   * fetches one of those pages. The returned payload has the same
   * columnar shape as `filings.recent`.
   */
  async getCompanySubmissionsPage(
    pageName: string,
  ): Promise<Record<string, any>> {
    const url = `${SEC_BASE_URL}/submissions/${pageName}`;
    return await this.httpClient.get(url);
  }

  /**
   * Get recent filings across all companies via the SEC EDGAR Atom feed.
   *
   * @param formType Form type(s) to filter by (e.g., "8-K", ["3", "4", "5"])
   * @param limit Maximum number of filings to return (feed max 100/page)
   * @param owner Ownership-filing filter: "include", "exclude", or "only"
   * @param start Pagination offset
   */
  async getRecentFilings(
    formType?: string | string[],
    limit: number = 40,
    owner: "include" | "exclude" | "only" = "include",
    start: number = 0,
  ): Promise<RecentFilingEntry[]> {
    const formTypes =
      formType == null
        ? [undefined]
        : Array.isArray(formType)
          ? formType
          : [formType];

    const entries: RecentFilingEntry[] = [];
    for (const type of formTypes) {
      const params = new URLSearchParams({
        action: "getcurrent",
        output: "atom",
        owner,
        count: String(Math.min(limit, 100)),
        start: String(start),
      });
      if (type) {
        params.set("type", type);
      }
      try {
        const feed = await this.httpClient.getRaw(
          `${SEC_CURRENT_FILINGS_URL}?${params.toString()}`,
        );
        entries.push(...FilingsEndpoints.parseAtomFeed(feed));
      } catch {
        // A failed feed request degrades to an empty page for that type
      }
    }

    entries.sort((a, b) =>
      a.filingDate < b.filingDate ? 1 : a.filingDate > b.filingDate ? -1 : 0,
    );
    return entries.slice(0, limit);
  }

  /** Parse the browse-edgar Atom feed into filing entries. */
  static parseAtomFeed(feed: string): RecentFilingEntry[] {
    const entries: RecentFilingEntry[] = [];
    const entryPattern = /<entry>([\s\S]*?)<\/entry>/g;
    let entryMatch;
    while ((entryMatch = entryPattern.exec(feed)) !== null) {
      const block = entryMatch[1];
      const title = (block.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || "";
      // Title format: "10-K - Company Name (0001234567) (Filer)"
      const titleMatch = title.match(/^\s*(.+?)\s+-\s+(.*?)\s+\((\d{10})\)/);
      const link = (block.match(/<link[^>]*href="([^"]+)"/) || [])[1] || "";
      const accession =
        (block.match(/accession[-_]?number[^>]*>([\d-]+)</i) || [])[1] ||
        (link.match(/(\d{10}-\d{2}-\d{6})/) || [])[1] ||
        "";
      const updated = (block.match(/<updated>([\d-]+)/) || [])[1] || "";

      if (titleMatch) {
        entries.push({
          formType: titleMatch[1].trim(),
          companyName: titleMatch[2].trim(),
          cik: titleMatch[3],
          accessionNumber: accession,
          filingDate: updated,
          url: link,
        });
      }
    }
    return entries;
  }

  private filterSubmissions(
    submissions: CompanySubmissions,
    options: RequestOptions,
  ): CompanySubmissions {
    if (!submissions.filings || !submissions.filings.recent) {
      return submissions;
    }

    const { recent } = submissions.filings;
    let indices = recent.accessionNumber.map((_: any, index: number) => index);

    // Filter by submission type
    if (options.submissionType) {
      indices = indices.filter(
        (i: number) => recent.form[i] === options.submissionType,
      );
    }

    // Filter by date range
    if (options.fromDate || options.toDate) {
      indices = indices.filter((i: number) => {
        const filingDate = recent.filingDate[i];
        if (options.fromDate && filingDate < options.fromDate) return false;
        if (options.toDate && filingDate > options.toDate) return false;
        return true;
      });
    }

    // Create filtered results
    const filteredRecent: Record<string, any> = {};
    Object.keys(recent).forEach((key) => {
      filteredRecent[key] = indices.map((i: number) => recent[key][i]);
    });

    return {
      ...submissions,
      filings: {
        ...submissions.filings,
        recent: filteredRecent,
      },
    };
  }
}
