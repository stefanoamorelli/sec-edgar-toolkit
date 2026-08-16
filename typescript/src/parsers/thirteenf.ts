/**
 * Parser for Form 13F institutional holdings reports.
 *
 * A 13F filing has two XML documents: the information table (one
 * `infoTable` entry per position) and the primary document (cover page
 * with the filing manager, report period, and summary totals). Matching
 * is namespace-agnostic so schema-version changes don't break it.
 */

import { XMLParser } from "fast-xml-parser";

export interface ThirteenFHolding {
  nameOfIssuer: string;
  titleOfClass: string;
  cusip: string;
  value: number;
  sharesOrPrincipalAmount: number;
  sharesOrPrincipalType: string;
  putCall: string;
  investmentDiscretion: string;
  otherManager: string;
  votingAuthority: { sole: number; shared: number; none: number };
}

export interface ThirteenFCoverPage {
  managerName: string;
  periodOfReport: string;
  reportType: string;
  isAmendment: boolean;
  tableEntryTotal: number;
  tableValueTotal: number;
}

function localName(tag: string): string {
  return tag.includes(":") ? tag.slice(tag.indexOf(":") + 1) : tag;
}

function asArray<T>(value: T | T[] | undefined): T[] {
  if (value === undefined || value === null) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
}

function findDeep(obj: any, name: string): any {
  if (obj === null || typeof obj !== "object") {
    return undefined;
  }
  for (const [key, value] of Object.entries(obj)) {
    if (localName(key) === name) {
      return value;
    }
  }
  for (const value of Object.values(obj)) {
    const found = findDeep(value, name);
    if (found !== undefined) {
      return found;
    }
  }
  return undefined;
}

function text(value: any): string {
  if (value === undefined || value === null) {
    return "";
  }
  if (typeof value === "object") {
    return String(value["#text"] ?? "").trim();
  }
  return String(value).trim();
}

function num(value: any): number {
  const raw = text(value).replace(/,/g, "");
  if (!raw) {
    return 0;
  }
  const parsed = Number(raw);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function parseXml(raw: string): any {
  const parser = new XMLParser({
    ignoreAttributes: false,
    parseTagValue: false,
    trimValues: true,
  });
  return parser.parse(raw);
}

export class ThirteenFParser {
  private readonly root: any;

  constructor(informationTableXml: string) {
    this.root = parseXml(informationTableXml);
  }

  /** Parse every position in the information table. */
  parseHoldings(): ThirteenFHolding[] {
    const table = findDeep(this.root, "informationTable") ?? this.root;
    const entries = asArray(findDeep(table, "infoTable"));

    const holdings: ThirteenFHolding[] = [];
    for (const entry of entries) {
      const byLocal: Record<string, any> = {};
      for (const [key, value] of Object.entries(entry)) {
        byLocal[localName(key)] = value;
      }

      const sharesElem = byLocal.shrsOrPrnAmt;
      const votingElem = byLocal.votingAuthority;

      holdings.push({
        nameOfIssuer: text(byLocal.nameOfIssuer),
        titleOfClass: text(byLocal.titleOfClass),
        cusip: text(byLocal.cusip),
        value: num(byLocal.value),
        sharesOrPrincipalAmount: num(findDeep(sharesElem, "sshPrnamt")),
        sharesOrPrincipalType: text(findDeep(sharesElem, "sshPrnamtType")),
        putCall: text(byLocal.putCall),
        investmentDiscretion: text(byLocal.investmentDiscretion),
        otherManager: text(byLocal.otherManager),
        votingAuthority: {
          sole: num(findDeep(votingElem, "Sole")),
          shared: num(findDeep(votingElem, "Shared")),
          none: num(findDeep(votingElem, "None")),
        },
      });
    }
    return holdings;
  }

  /** Parse the primary document's cover page. */
  static parseCoverPage(primaryDocXml: string): ThirteenFCoverPage {
    const root = parseXml(primaryDocXml);
    const manager = findDeep(root, "filingManager");
    return {
      managerName: text(findDeep(manager, "name")),
      periodOfReport: text(findDeep(root, "periodOfReport")),
      reportType: text(findDeep(root, "reportType")),
      isAmendment: text(findDeep(root, "isAmendment")).toLowerCase() === "true",
      tableEntryTotal: num(findDeep(root, "tableEntryTotal")),
      tableValueTotal: num(findDeep(root, "tableValueTotal")),
    };
  }
}
