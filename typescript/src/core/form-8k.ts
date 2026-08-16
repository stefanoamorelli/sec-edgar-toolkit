/**
 * Structured view of an 8-K current report, returned by `Filing.obj()`.
 */

import { EightKItem } from "../parsers/items";
import { Attachment } from "./attachments";

const DATE_OF_REPORT_RE =
  /Date\s+of\s+Report[^:]{0,80}:?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})/;

const ITEM_CODE_RE = /\bItem\s+(\d\.\d{2})/gi;

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export interface EightKData {
  items: string[];
  dateOfReport: string | null;
  attachments: Attachment[];
  pressReleases: Array<{ document: string; url: string; size?: number }>;
  hasPressRelease: boolean;
}

/** 8-K current report: reported items, date of report, press releases. */
export class EightK {
  public readonly items: string[];
  public readonly dateOfReport: string | null;
  public readonly attachments: Attachment[];
  public readonly pressReleases: Array<{
    document: string;
    url: string;
    size?: number;
  }>;
  public readonly hasPressRelease: boolean;

  private constructor(data: EightKData) {
    this.items = data.items;
    this.dateOfReport = data.dateOfReport;
    this.attachments = data.attachments;
    this.pressReleases = data.pressReleases;
    this.hasPressRelease = data.hasPressRelease;
  }

  static async create(filing: {
    text(format?: string): Promise<string>;
    getAttachments(): Promise<Attachment[]>;
    periodOfReport?: string;
  }): Promise<EightK> {
    const raw = await filing.text("raw");
    const clean = await filing.text();

    // Items present in the report body (the canonical "Item N.NN" marker)
    const codes: string[] = [];
    let match;
    ITEM_CODE_RE.lastIndex = 0;
    while ((match = ITEM_CODE_RE.exec(clean)) !== null) {
      if (!codes.includes(match[1])) {
        codes.push(match[1]);
      }
    }

    let dateOfReport: string | null = null;
    for (const source of [clean, raw]) {
      const dateMatch = source.match(DATE_OF_REPORT_RE);
      if (dateMatch) {
        dateOfReport = dateMatch[1].replace(/\s+/g, " ").trim();
        break;
      }
    }
    if (!dateOfReport && filing.periodOfReport) {
      const parsed = new Date(`${filing.periodOfReport}T00:00:00Z`);
      if (!Number.isNaN(parsed.getTime())) {
        dateOfReport = `${MONTH_NAMES[parsed.getUTCMonth()]} ${parsed.getUTCDate()}, ${parsed.getUTCFullYear()}`;
      } else {
        dateOfReport = String(filing.periodOfReport);
      }
    }

    const attachments = await filing.getAttachments();
    const press = attachments.filter((attachment) => attachment.isPressRelease);

    return new EightK({
      items: codes,
      dateOfReport,
      attachments,
      pressReleases: press.map((attachment) => attachment.toObject()),
      hasPressRelease: press.length > 0,
    });
  }

  /**
   * True when the given item is present.
   * Accepts an `EightKItem` or a string (`"2.02"` / `"Item 2.02"`).
   */
  hasItem(itemCode: string | EightKItem): boolean {
    const code = String(itemCode).replace("Item", "").trim();
    return this.items.includes(code);
  }
}
