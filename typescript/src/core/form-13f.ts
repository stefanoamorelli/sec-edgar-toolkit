/**
 * Structured view of a Form 13F holdings report, returned by `Filing.obj()`.
 */

import {
  ThirteenFCoverPage,
  ThirteenFHolding,
  ThirteenFParser,
} from "../parsers/thirteenf";

export class Holding13F {
  public readonly nameOfIssuer: string;
  public readonly titleOfClass: string;
  public readonly cusip: string;
  public readonly value: number;
  public readonly shares: number;
  public readonly sharesType: string;
  public readonly putCall: string;
  public readonly investmentDiscretion: string;
  public readonly otherManager: string;
  public readonly votingAuthority: {
    sole: number;
    shared: number;
    none: number;
  };

  constructor(data: ThirteenFHolding) {
    this.nameOfIssuer = data.nameOfIssuer;
    this.titleOfClass = data.titleOfClass;
    this.cusip = data.cusip;
    this.value = data.value;
    this.shares = data.sharesOrPrincipalAmount;
    this.sharesType = data.sharesOrPrincipalType;
    this.putCall = data.putCall;
    this.investmentDiscretion = data.investmentDiscretion;
    this.otherManager = data.otherManager;
    this.votingAuthority = data.votingAuthority;
  }
}

interface ThirteenFFiling {
  getAttachments(): Promise<Array<{ document: string; url: string }>>;
  api: { httpClient: { getRaw(url: string): Promise<string> } };
}

export class ThirteenF {
  public readonly holdings: Holding13F[];
  public readonly managerName: string;
  public readonly periodOfReport: string;
  public readonly reportType: string;
  public readonly isAmendment: boolean;
  public readonly reportedEntryTotal: number;
  public readonly reportedValueTotal: number;

  constructor(holdings: ThirteenFHolding[], cover?: ThirteenFCoverPage | null) {
    this.holdings = holdings.map((h) => new Holding13F(h));
    this.managerName = cover?.managerName || "";
    this.periodOfReport = cover?.periodOfReport || "";
    this.reportType = cover?.reportType || "";
    this.isAmendment = Boolean(cover?.isAmendment);
    this.reportedEntryTotal = cover?.tableEntryTotal || 0;
    this.reportedValueTotal = cover?.tableValueTotal || 0;
  }

  get holdingCount(): number {
    return this.holdings.length;
  }

  /** Sum of position values as reported (USD). */
  get totalValue(): number {
    return this.holdings.reduce((sum, holding) => sum + holding.value, 0);
  }

  /** Positions whose issuer name contains `name` (case-insensitive). */
  byIssuer(name: string): Holding13F[] {
    const needle = name.toLowerCase();
    return this.holdings.filter((holding) =>
      holding.nameOfIssuer.toLowerCase().includes(needle),
    );
  }

  /** The `n` largest positions by reported value. */
  topHoldings(n: number = 10): Holding13F[] {
    return this.holdings
      .slice()
      .sort((a, b) => b.value - a.value)
      .slice(0, n);
  }

  /**
   * Build a ThirteenF from a filing by locating the information table
   * and primary document in its archive folder.
   */
  static async fromFiling(filing: ThirteenFFiling): Promise<ThirteenF> {
    let tableXml: string | null = null;
    let primaryXml: string | null = null;

    for (const attachment of await filing.getAttachments()) {
      const name = attachment.document.toLowerCase();
      if (!name.endsWith(".xml")) {
        continue;
      }
      try {
        if (name === "primary_doc.xml") {
          primaryXml = await filing.api.httpClient.getRaw(attachment.url);
        } else if (tableXml === null) {
          const content = await filing.api.httpClient.getRaw(attachment.url);
          if (content.includes("informationTable")) {
            tableXml = content;
          }
        }
      } catch {
        continue;
      }
    }

    if (tableXml === null) {
      throw new Error("No 13F information table found in the filing");
    }

    const holdings = new ThirteenFParser(tableXml).parseHoldings();
    const cover = primaryXml
      ? ThirteenFParser.parseCoverPage(primaryXml)
      : null;
    return new ThirteenF(holdings, cover);
  }
}
