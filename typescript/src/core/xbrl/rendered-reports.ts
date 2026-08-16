/**
 * Reader for a filing's rendered reports.
 *
 * Every XBRL filing ships with `FilingSummary.xml` (the list of rendered
 * reports, with roles and long names) and one `R<n>.htm` file per report
 * (the rendered statement table). This module handles fetching and
 * caching; the actual HTML parsing lives in `report-html-parser`.
 */

import { parseReportHtml, StatementLineItem } from "./report-html-parser";

export interface ReportDescriptor {
  definition: string;
  shortName: string;
  role: string;
  rFile: string;
  reportType: string;
}

interface RawHttpClient {
  getRaw(url: string): Promise<string>;
}

function findXmlText(block: string, tag: string): string {
  const match = block.match(new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`));
  return match ? match[1].trim() : "";
}

/**
 * Lists and parses a filing's rendered reports.
 *
 * Only depends on an HTTP client (`getRaw(url)`) and the filing's
 * archive-folder base URL, so it is reusable outside `XBRLInstance`.
 */
export class RenderedReportReader {
  private readonly archiveBase: string;
  private readonly http: RawHttpClient;
  private reports: ReportDescriptor[] | null = null;
  private readonly statementCache = new Map<string, StatementLineItem[]>();

  constructor(archiveBase: string, http: RawHttpClient) {
    this.archiveBase = archiveBase;
    this.http = http;
  }

  /** Parse FilingSummary.xml into a list of report descriptors. */
  async listReports(): Promise<ReportDescriptor[]> {
    if (this.reports !== null) {
      return this.reports;
    }

    let raw: string;
    try {
      raw = await this.http.getRaw(`${this.archiveBase}/FilingSummary.xml`);
    } catch {
      this.reports = [];
      return this.reports;
    }

    const reports: ReportDescriptor[] = [];
    const reportPattern = /<Report[^>]*>([\s\S]*?)<\/Report>/g;
    let match;
    while ((match = reportPattern.exec(raw)) !== null) {
      const block = match[1];
      const descriptor: ReportDescriptor = {
        definition: findXmlText(block, "LongName"),
        shortName: findXmlText(block, "ShortName"),
        role: findXmlText(block, "Role"),
        rFile: findXmlText(block, "HtmlFileName"),
        reportType: findXmlText(block, "ReportType"),
      };
      if (descriptor.role || descriptor.rFile) {
        reports.push(descriptor);
      }
    }

    this.reports = reports;
    return reports;
  }

  /** Find a report by role URI, R-file name, or short name. */
  async findReport(role: string): Promise<ReportDescriptor | null> {
    const reports = await this.listReports();
    for (const report of reports) {
      if (
        role === report.role ||
        role === report.rFile ||
        role === report.shortName
      ) {
        return report;
      }
    }
    const roleLower = role.toLowerCase();
    for (const report of reports) {
      if (report.role.toLowerCase().endsWith(roleLower)) {
        return report;
      }
    }
    return null;
  }

  /**
   * Parse one rendered report into line items.
   *
   * @param role The report's role URI (from `listReports()`), its R-file
   *   name, or its short name.
   */
  async readStatement(role: string): Promise<StatementLineItem[]> {
    const report = await this.findReport(role);
    if (!report || !report.rFile) {
      return [];
    }

    const cached = this.statementCache.get(report.rFile);
    if (cached) {
      return cached;
    }

    let raw: string;
    try {
      raw = await this.http.getRaw(`${this.archiveBase}/${report.rFile}`);
    } catch {
      return [];
    }

    const items = parseReportHtml(raw);
    this.statementCache.set(report.rFile, items);
    return items;
  }
}
