/**
 * Structured view of a 10-K annual report, returned by `Filing.obj()`.
 */

import { TenKItem } from "../parsers/items";
import { PeriodicReport, ReportFiling } from "./periodic-report";

/** 10-K annual report: named sections and XBRL-backed financials. */
export class TenK extends PeriodicReport {
  static SECTION_ITEMS: Record<string, string> = {
    business: TenKItem.BUSINESS,
    riskFactors: TenKItem.RISK_FACTORS,
    mda: TenKItem.MANAGEMENT_DISCUSSION_AND_ANALYSIS,
  };

  static async create(filing: ReportFiling): Promise<TenK> {
    let items: Record<string, string> = {};
    try {
      items = await filing.extractItems();
    } catch {
      items = {};
    }
    return new TenK(filing, items);
  }
}
