/**
 * Shared base for periodic report objects (10-K, 10-Q).
 *
 * Sections (`business`, `riskFactors`, `mda`) are extracted from the
 * document by item number; only sections that were actually found are
 * set, so callers can feature-detect with `in` / `!== undefined`.
 */

import { Financials } from "./financials";

export interface ReportFiling {
  extractItems(): Promise<Record<string, string>>;
  cik: string;
  formType?: string;
  accessionNumber?: string;
  api: { getCompanyFacts(cik: string): Promise<Record<string, any>> };
}

export abstract class PeriodicReport {
  protected readonly filing: ReportFiling;
  public readonly items: Record<string, string>;

  public readonly business?: string;
  public readonly riskFactors?: string;
  public readonly mda?: string;

  protected constructor(filing: ReportFiling, items: Record<string, string>) {
    this.filing = filing;
    this.items = items;

    const sections = (this.constructor as typeof PeriodicReport).SECTION_ITEMS;
    for (const [attribute, itemKey] of Object.entries(sections)) {
      const content = items[itemKey];
      if (content) {
        (this as Record<string, unknown>)[attribute] = content;
      }
    }
  }

  /** mapping of section attribute -> item key in the extracted-items map */
  static SECTION_ITEMS: Record<string, string> = {};

  /** Financial statements backed by XBRL company facts. */
  async financials(): Promise<Financials> {
    return Financials.extract(this.filing);
  }
}
