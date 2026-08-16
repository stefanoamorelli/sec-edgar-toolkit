/**
 * Company class of the object API.
 *
 * Represents a company and provides access to its filings, financial
 * data, and profile information from the SEC database.
 */

import { EdgarClient } from "../client/edgar-client";
import { Filings } from "./collections";
import { CompanyFacts } from "./facts";
import { Filing } from "./filing";
import { Financials } from "./financials";

export interface GetFilingsOptions {
  /** Form type(s) to filter by (e.g., "10-K", ["10-K", "10-Q"]). */
  form?: string | string[];
  /** Start date (YYYY-MM-DD). */
  since?: string;
  /** End date (YYYY-MM-DD). */
  before?: string;
  /** Maximum number of filings to return. */
  limit?: number;
  /**
   * Also walk the older-history pages beyond the ~1000 most recent
   * filings (one extra request per page).
   */
  deep?: boolean;
  /** Also match amended variants of the requested forms ("10-K/A"). */
  amendments?: boolean;
}

export class Company {
  public readonly api: EdgarClient;
  /** 10-digit, zero-padded CIK. */
  public readonly cik: string;
  public readonly name: string;
  public readonly ticker: string;
  public readonly exchange: string;

  private submissionsCache: Record<string, any> | null = null;
  private factsCache: CompanyFacts | null = null;

  private constructor(
    api: EdgarClient,
    cik: string,
    name: string,
    ticker: string,
    exchange: string,
  ) {
    this.api = api;
    this.cik = cik;
    this.name = name;
    this.ticker = ticker;
    this.exchange = exchange;
  }

  /**
   * Resolve a company by ticker or CIK.
   *
   * @throws Error when the identifier cannot be resolved
   */
  static async lookup(
    identifier: string | number,
    api?: EdgarClient,
  ): Promise<Company> {
    const client = api || (await import("./global-functions")).getApi();
    const idStr = String(identifier);

    let data = null;
    if (!/^\d+$/.test(idStr)) {
      data = await client.getCompanyByTicker(idStr);
    }
    if (!data && /^\d+$/.test(idStr)) {
      data = await client.getCompanyByCik(idStr.padStart(10, "0"));
    }

    if (data) {
      return new Company(
        client,
        data.cik_str,
        data.title,
        data.ticker || "",
        data.exchange || "",
      );
    }

    // Filers without a listed ticker still resolve through submissions
    if (/^\d+$/.test(idStr)) {
      const cik = idStr.padStart(10, "0");
      const submissions = await client.getCompanySubmissions(cik);
      if (submissions && submissions.name) {
        const tickers: string[] =
          (submissions as Record<string, any>).tickers || [];
        const exchanges: string[] =
          (submissions as Record<string, any>).exchanges || [];
        const company = new Company(
          client,
          cik,
          submissions.name,
          tickers[0] || "",
          exchanges[0] || "",
        );
        company.submissionsCache = submissions as Record<string, any>;
        return company;
      }
    }

    throw new Error(`Company not found: ${identifier}`);
  }

  /** The raw submissions payload (profile + recent filing history). */
  async profile(): Promise<Record<string, any>> {
    if (this.submissionsCache === null) {
      try {
        this.submissionsCache = (await this.api.getCompanySubmissions(
          this.cik,
        )) as Record<string, any>;
      } catch {
        this.submissionsCache = {};
      }
    }
    return this.submissionsCache;
  }

  /** SIC code from the company profile. */
  async sic(): Promise<string> {
    return (await this.profile()).sic || "";
  }

  /** SIC description from the company profile. */
  async sicDescription(): Promise<string> {
    return (await this.profile()).sicDescription || "";
  }

  /** State of incorporation from the company profile. */
  async stateOfIncorporation(): Promise<string> {
    return (await this.profile()).stateOfIncorporation || "";
  }

  /** Fiscal year end (MMDD) from the company profile. */
  async fiscalYearEnd(): Promise<string> {
    return (await this.profile()).fiscalYearEnd || "";
  }

  /** All ticker symbols for this company. */
  async tickers(): Promise<string[]> {
    const submissions = await this.profile();
    const tickers: string[] = submissions.tickers || [];
    if (tickers.length > 0) {
      return tickers;
    }
    return this.ticker ? [this.ticker] : [];
  }

  /** Filings for this company, newest first. */
  async getFilings(options: GetFilingsOptions = {}): Promise<Filings> {
    const { form, since, before, limit, deep, amendments } = options;

    const submissions = (await this.api.getCompanySubmissions(this.cik, {
      fromDate: since,
      toDate: before,
    })) as Record<string, any>;

    const formTypes: string[] =
      form == null ? [] : Array.isArray(form) ? [...form] : [form];
    if (amendments) {
      for (const formType of [...formTypes]) {
        if (!formType.endsWith("/A")) {
          formTypes.push(`${formType}/A`);
        }
      }
    }

    const filings = new Filings();
    const filingsData = submissions.filings || {};

    this.appendFilings(filings, filingsData.recent || {}, formTypes, limit);

    if (deep && !(limit && filings.length >= limit)) {
      for (const page of filingsData.files || []) {
        if (since && page.filingTo && page.filingTo < since) {
          continue;
        }
        let pageData: Record<string, any>;
        try {
          pageData = await this.api.filings.getCompanySubmissionsPage(
            page.name,
          );
        } catch {
          continue;
        }
        this.appendFilings(filings, pageData, formTypes, limit);
        if (limit && filings.length >= limit) {
          break;
        }
      }
    }

    return filings;
  }

  private appendFilings(
    filings: Filings,
    columns: Record<string, any>,
    formTypes: string[],
    limit?: number,
  ): void {
    const accessionNumbers: string[] = columns.accessionNumber || [];
    const formList: string[] = columns.form || [];
    const filingDates: string[] = columns.filingDate || [];
    const fileNumbers: string[] = columns.fileNumber || [];
    const acceptanceDatetimes: string[] = columns.acceptanceDateTime || [];
    const reportDates: string[] = columns.reportDate || [];
    const primaryDocuments: string[] = columns.primaryDocument || [];
    const sizes: number[] = columns.size || [];

    const column = <T>(values: T[], index: number): T | undefined =>
      index < values.length ? values[index] : undefined;

    for (let i = 0; i < accessionNumbers.length; i++) {
      if (i >= formList.length || i >= filingDates.length) {
        break;
      }

      const filingForm = formList[i];
      if (formTypes.length > 0 && !formTypes.includes(filingForm)) {
        continue;
      }

      filings.push(
        new Filing({
          cik: this.cik,
          accessionNumber: accessionNumbers[i],
          formType: filingForm,
          filingDate: filingDates[i],
          api: this.api,
          companyName: this.name,
          fileNumber: column(fileNumbers, i),
          acceptanceDatetime: column(acceptanceDatetimes, i),
          periodOfReport: column(reportDates, i),
          primaryDocument: column(primaryDocuments, i),
          size: column(sizes, i),
        }),
      );

      if (limit && filings.length >= limit) {
        break;
      }
    }
  }

  /** XBRL company facts (`.data` mapping plus `getFact(concept)`). */
  async getFacts(): Promise<CompanyFacts> {
    if (this.factsCache === null) {
      this.factsCache = new CompanyFacts(
        await this.api.getCompanyFacts(this.cik),
      );
    }
    return this.factsCache;
  }

  /** The raw XBRL company-facts payload. */
  async getCompanyFacts(): Promise<Record<string, any>> {
    return (await this.getFacts()).raw;
  }

  /** Annual financial statements (from 10-K facts). */
  async getFinancials(): Promise<Financials> {
    const facts = await this.getFacts();
    return new Financials(facts.raw, "10-K");
  }

  /** Quarterly financial statements (from 10-Q facts). */
  async getQuarterlyFinancials(): Promise<Financials> {
    const facts = await this.getFacts();
    return new Financials(facts.raw, "10-Q");
  }

  /** Historical data for one XBRL concept. */
  async getConcept(
    taxonomy: string,
    tag: string,
    unit?: string,
  ): Promise<Record<string, any>> {
    return this.api.getCompanyConcept(this.cik, taxonomy, tag, unit);
  }

  toString(): string {
    return this.ticker
      ? `${this.ticker}: ${this.name}`
      : `CIK ${this.cik}: ${this.name}`;
  }
}
