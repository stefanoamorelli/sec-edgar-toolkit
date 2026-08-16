/**
 * Filing class of the object API.
 *
 * Represents a single SEC filing and provides access to its content,
 * documents, structured data, and XBRL information.
 */

import { EdgarClient } from "../client/edgar-client";
import { ItemExtractor } from "../parsers/item-extractor";
import { FilingItem } from "../parsers/items";
import { OwnershipFormParser } from "../parsers/ownership-forms";
import { Attachment } from "./attachments";
import { EightK } from "./form-8k";
import { TenK } from "./form-10k";
import { TenQ } from "./form-10q";
import { OwnershipForm } from "./ownership";
import { XBRLInstance } from "./xbrl";

const ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data";

export interface FilingProps {
  cik: string | number;
  accessionNumber: string;
  formType: string;
  filingDate: string;
  api: EdgarClient;
  companyName?: string;
  periodOfReport?: string;
  acceptanceDatetime?: string;
  fileNumber?: string;
  primaryDocument?: string;
  size?: number;
}

export type FilingObject =
  OwnershipForm | EightK | TenK | TenQ | Record<string, any>;

export class Filing {
  public readonly api: EdgarClient;
  /** 10-digit, zero-padded CIK. */
  public readonly cik: string;
  /** Dashed accession number. */
  public readonly accessionNumber: string;
  public readonly formType: string;
  /** ISO date string (YYYY-MM-DD). */
  public readonly filingDate: string;
  public readonly companyName: string;
  public readonly periodOfReport: string;
  public readonly acceptanceDatetime: string;
  public readonly fileNumber: string;
  public readonly primaryDocument: string;
  public readonly size: number;
  /** URL of the filing index page. */
  public readonly url: string;

  private details: Record<string, any> | null = null;
  private textContent: string | null = null;
  private objContent: FilingObject | null = null;
  private xbrlInstance: XBRLInstance | null = null;
  private extractedItems: Record<string, string> | null = null;
  private attachmentList: Attachment[] | null = null;
  private readonly itemExtractor = new ItemExtractor();

  constructor(props: FilingProps) {
    this.api = props.api;
    this.cik = String(props.cik).padStart(10, "0");
    this.accessionNumber = props.accessionNumber;
    this.formType = props.formType;
    this.filingDate = String(props.filingDate).slice(0, 10);
    this.companyName = props.companyName || "";
    this.periodOfReport = props.periodOfReport || "";
    this.acceptanceDatetime = props.acceptanceDatetime || "";
    this.fileNumber = props.fileNumber || "";
    this.primaryDocument = props.primaryDocument || "";
    this.size = props.size || 0;
    this.url = `${this.archiveBase}/${this.accessionNumber}-index.htm`;
  }

  get archiveBase(): string {
    const accessionClean = this.accessionNumber.replace(/-/g, "");
    return `${ARCHIVES_BASE}/${parseInt(this.cik, 10)}/${accessionClean}`;
  }

  private async getDetails(): Promise<Record<string, any>> {
    if (this.details === null) {
      try {
        this.details = await this.api.getFiling(this.cik, this.accessionNumber);
      } catch {
        this.details = {};
      }
    }
    return this.details;
  }

  private async directoryItems(): Promise<Array<Record<string, any>>> {
    const details = await this.getDetails();
    const items = details?.directory?.item;
    return Array.isArray(items) ? items : [];
  }

  /** All documents in the filing's archive folder. */
  async getAttachments(): Promise<Attachment[]> {
    if (this.attachmentList === null) {
      const items = await this.directoryItems();
      this.attachmentList = items
        .filter((item) => item.name && !String(item.name).endsWith("/"))
        .map(
          (item) =>
            new Attachment(
              item.name,
              `${this.archiveBase}/${item.name}`,
              item.size ? Number(item.size) : undefined,
            ),
        );
    }
    return this.attachmentList;
  }

  private async pickMainDocument(): Promise<string> {
    if (this.primaryDocument) {
      return this.primaryDocument;
    }

    let mainDocument: string | null = null;
    for (const item of await this.directoryItems()) {
      const name: string = item.name || "";
      const lower = name.toLowerCase();
      if (!lower.endsWith(".htm") && !lower.endsWith(".txt")) {
        continue;
      }
      if (lower.endsWith("-index.htm") || name.includes("/")) {
        continue;
      }
      const formToken = this.formType.toLowerCase().replace(/-/g, "");
      if (
        lower.endsWith(".htm") &&
        (lower.replace(/-/g, "").includes(formToken) ||
          lower.includes("filing"))
      ) {
        return name;
      }
      if (mainDocument === null) {
        mainDocument = name;
      }
    }

    // Fallback: the full-submission text file
    return mainDocument || `${this.accessionNumber}.txt`;
  }

  /**
   * Get the content of the filing's main document.
   *
   * @param format "text" (tags stripped), "html", or "raw"
   */
  async text(format: "text" | "html" | "raw" = "text"): Promise<string> {
    if (this.textContent === null) {
      const documentUrl = `${this.archiveBase}/${await this.pickMainDocument()}`;
      try {
        this.textContent = await this.api.httpClient.getRaw(documentUrl);
      } catch {
        this.textContent = "";
      }
    }

    if (format === "html" || format === "raw") {
      return this.textContent;
    }
    return Filing.cleanTextContent(this.textContent);
  }

  private static cleanTextContent(content: string): string {
    if (!content) {
      return "";
    }
    return content
      .replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;|&#160;/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  private async fetchOwnershipXml(): Promise<string | null> {
    for (const item of await this.directoryItems()) {
      const name: string = item.name || "";
      if (
        name.toLowerCase().endsWith(".xml") &&
        !name.toLowerCase().includes("xsl")
      ) {
        try {
          return await this.api.httpClient.getRaw(
            `${this.archiveBase}/${name}`,
          );
        } catch {
          continue;
        }
      }
    }

    // Fallback: extract the embedded XML from the full submission file
    const raw = await this.text("raw");
    const match = raw.match(/<ownershipDocument>[\s\S]*?<\/ownershipDocument>/);
    return match ? match[0] : null;
  }

  /**
   * Get a structured, form-specific view of the filing.
   *
   * - Forms 3/4/5: `OwnershipForm` (owner, transactions, holdings)
   * - 8-K: `EightK` (items, date of report, press releases)
   * - 10-K/10-Q: `TenK`/`TenQ` (sections and financials)
   * - Other forms: header-metadata object
   */
  async obj(): Promise<FilingObject> {
    if (this.objContent === null) {
      this.objContent = await this.parseStructuredContent();
    }
    return this.objContent;
  }

  private async parseStructuredContent(): Promise<FilingObject> {
    try {
      if (["3", "4", "5", "3/A", "4/A", "5/A"].includes(this.formType)) {
        const xml = await this.fetchOwnershipXml();
        if (!xml) {
          return { parseError: "No ownership XML document found" };
        }
        const parser = new OwnershipFormParser(xml);
        return new OwnershipForm(parser.parseAll());
      }
      if (this.formType === "8-K" || this.formType === "8-K/A") {
        return await EightK.create(this);
      }
      if (this.formType === "10-K" || this.formType === "10-K/A") {
        return await TenK.create(this);
      }
      if (this.formType === "10-Q" || this.formType === "10-Q/A") {
        return await TenQ.create(this);
      }
      return await this.parseGenericContent();
    } catch (error) {
      return { parseError: String(error) };
    }
  }

  private async parseGenericContent(): Promise<Record<string, any>> {
    const content = await this.text("raw");
    const result: Record<string, any> = {
      formType: this.formType,
      filingDate: this.filingDate,
      cik: this.cik,
      accessionNumber: this.accessionNumber,
    };

    const patterns: Record<string, RegExp> = {
      companyName: /COMPANY CONFORMED NAME:\s*([^\n\r]+)/i,
      sic: /STANDARD INDUSTRIAL CLASSIFICATION:\s*([^\n\r]+)/i,
      stateOfIncorporation: /STATE OF INCORPORATION:\s*([^\n\r]+)/i,
      fiscalYearEnd: /FISCAL YEAR END:\s*([^\n\r]+)/i,
    };

    for (const [field, pattern] of Object.entries(patterns)) {
      const match = content.match(pattern);
      if (match) {
        result[field] = match[1].trim();
      }
    }

    return result;
  }

  /**
   * Extract individual items from the filing (e.g., Item 1, Item 1A).
   *
   * @param itemNumbers Optional list of specific items, as strings
   *   ("1A") or item enums (`TenKItem.RISK_FACTORS`).
   */
  async extractItems(
    itemNumbers?: Array<string | FilingItem>,
  ): Promise<Record<string, string>> {
    if (this.extractedItems === null) {
      const content = await this.text();
      try {
        this.extractedItems = this.itemExtractor.extractItems(
          content,
          this.formType,
        );
      } catch {
        this.extractedItems = {};
      }
    }

    if (!itemNumbers) {
      return this.extractedItems;
    }
    const wanted = itemNumbers.map(String);
    const result: Record<string, string> = {};
    for (const [key, value] of Object.entries(this.extractedItems)) {
      if (wanted.includes(key)) {
        result[key] = value;
      }
    }
    return result;
  }

  /**
   * Get a specific item from the filing.
   *
   * Accepts a string ("1A") or an item enum
   * (`TenKItem.RISK_FACTORS`, `TenQItem.MDA`, `EightKItem...`).
   */
  async getItem(itemNumber: string | FilingItem): Promise<string | null> {
    const items = await this.extractItems([itemNumber]);
    return items[String(itemNumber)] ?? null;
  }

  /** XBRL instance for this filing. */
  xbrl(): XBRLInstance {
    if (this.xbrlInstance === null) {
      this.xbrlInstance = new XBRLInstance(this, this.api);
    }
    return this.xbrlInstance;
  }

  toString(): string {
    return `${this.formType} filing for CIK ${this.cik} on ${this.filingDate}`;
  }
}
