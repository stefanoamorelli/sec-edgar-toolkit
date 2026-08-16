/**
 * Structured view of a 10-Q quarterly report, returned by `Filing.obj()`.
 */

import { TenQItem } from "../parsers/items";
import { PeriodicReport, ReportFiling } from "./periodic-report";

/** 10-Q quarterly report: named sections and XBRL-backed financials. */
export class TenQ extends PeriodicReport {
  static SECTION_ITEMS: Record<string, string> = {
    mda: TenQItem.MANAGEMENT_DISCUSSION_AND_ANALYSIS,
    riskFactors: TenQItem.RISK_FACTORS,
  };

  static async create(filing: ReportFiling): Promise<TenQ> {
    let items: Record<string, string> = {};
    try {
      items = await filing.extractItems();
    } catch {
      items = {};
    }
    return new TenQ(filing, items);
  }
}
