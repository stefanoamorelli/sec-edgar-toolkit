/**
 * SEC Filing Item Extractor
 * 
 * Extracts individual items from SEC filings (10-K, 10-Q, 8-K, etc.)
 * based on standard item numbering and structure.
 */

import { InvalidFormTypeError } from '../exceptions/errors';

export enum FormType {
  FORM_10K = "10-K",
  FORM_10Q = "10-Q",
  FORM_8K = "8-K",
  FORM_20F = "20-F",
  FORM_40F = "40-F",
}

export interface ItemDefinition {
  number: string;
  title: string;
  aliases?: string[];
  required?: boolean;
}

export interface ExtractedItem {
  itemNumber: string;
  title: string;
  content: string;
  startPosition: number;
  endPosition: number;
}

export class ItemExtractor {
  // 10-K Item definitions
  private static readonly FORM_10K_ITEMS: ItemDefinition[] = [
    { number: "1", title: "Business" },
    { number: "1A", title: "Risk Factors" },
    { number: "1B", title: "Unresolved Staff Comments" },
    { number: "1C", title: "Cybersecurity", required: false },
    { number: "2", title: "Properties" },
    { number: "3", title: "Legal Proceedings" },
    { number: "4", title: "Mine Safety Disclosures", required: false },
    { number: "5", title: "Market for Registrant's Common Equity" },
    { number: "6", title: "Reserved", required: false },
    { number: "7", title: "Management's Discussion and Analysis", aliases: ["MD&A"] },
    { number: "7A", title: "Quantitative and Qualitative Disclosures About Market Risk" },
    { number: "8", title: "Financial Statements and Supplementary Data" },
    { number: "9", title: "Changes in and Disagreements with Accountants" },
    { number: "9A", title: "Controls and Procedures" },
    { number: "9B", title: "Other Information" },
    { number: "9C", title: "Disclosure Regarding Foreign Jurisdictions", required: false },
    { number: "10", title: "Directors, Executive Officers and Corporate Governance" },
    { number: "11", title: "Executive Compensation" },
    { number: "12", title: "Security Ownership" },
    { number: "13", title: "Certain Relationships and Related Transactions" },
    { number: "14", title: "Principal Accountant Fees and Services" },
    { number: "15", title: "Exhibits and Financial Statement Schedules" },
  ];

  // 10-Q Item definitions
  private static readonly FORM_10Q_ITEMS: ItemDefinition[] = [
    { number: "1", title: "Financial Statements" },
    { number: "2", title: "Management's Discussion and Analysis", aliases: ["MD&A"] },
    { number: "3", title: "Quantitative and Qualitative Disclosures About Market Risk" },
    { number: "4", title: "Controls and Procedures" },
    { number: "1", title: "Legal Proceedings", aliases: ["Part II, Item 1"] },
    { number: "1A", title: "Risk Factors", aliases: ["Part II, Item 1A"] },
    { number: "2", title: "Unregistered Sales of Equity Securities", aliases: ["Part II, Item 2"] },
    { number: "3", title: "Defaults Upon Senior Securities", aliases: ["Part II, Item 3"] },
    { number: "4", title: "Mine Safety Disclosures", aliases: ["Part II, Item 4"], required: false },
    { number: "5", title: "Other Information", aliases: ["Part II, Item 5"] },
    { number: "6", title: "Exhibits", aliases: ["Part II, Item 6"] },
  ];

  // 8-K Item definitions
  private static readonly FORM_8K_ITEMS: ItemDefinition[] = [
    { number: "1.01", title: "Entry into a Material Definitive Agreement" },
    { number: "1.02", title: "Termination of a Material Definitive Agreement" },
    { number: "2.01", title: "Completion of Acquisition or Disposition of Assets" },
    { number: "2.02", title: "Results of Operations and Financial Condition" },
    { number: "2.03", title: "Creation of a Direct Financial Obligation" },
    { number: "3.01", title: "Notice of Delisting or Failure to Satisfy" },
    { number: "3.02", title: "Unregistered Sales of Equity Securities" },
    { number: "4.01", title: "Changes in Registrant's Certifying Accountant" },
    { number: "4.02", title: "Non-Reliance on Previously Issued Financial Statements" },
    { number: "5.01", title: "Changes in Control of Registrant" },
    { number: "5.02", title: "Departure of Directors or Certain Officers" },
    { number: "5.03", title: "Amendments to Articles of Incorporation or Bylaws" },
    { number: "7.01", title: "Regulation FD Disclosure" },
    { number: "8.01", title: "Other Events" },
    { number: "9.01", title: "Financial Statements and Exhibits" },
  ];

  private readonly formItems: Map<FormType, ItemDefinition[]>;

  constructor() {
    this.formItems = new Map([
      [FormType.FORM_10K, ItemExtractor.FORM_10K_ITEMS],
      [FormType.FORM_10Q, ItemExtractor.FORM_10Q_ITEMS],
      [FormType.FORM_8K, ItemExtractor.FORM_8K_ITEMS],
    ]);
  }

  /**
   * Extract all items from a filing
   * @param content The filing content (HTML or text)
   * @param formType The type of form (e.g., "10-K", "10-Q", "8-K")
   * @returns Dictionary mapping item numbers to their content
   */
  extractItems(content: string, formType: string | FormType): Record<string, string> {
    // Convert string form type to enum
    const parsedFormType = typeof formType === 'string' ? this.parseFormType(formType) : formType;

    if (!this.formItems.has(parsedFormType)) {
      throw new InvalidFormTypeError(formType.toString(), ['10-K', '10-Q', '8-K', '20-F', '40-F']);
    }

    // Clean content
    const cleanContent = this.cleanContent(content);

    // Extract table of contents if available
    const tocItems = this.extractTableOfContents(cleanContent);

    // Extract items
    const items = this.extractItemsFromContent(cleanContent, parsedFormType, tocItems);

    // Post-process and validate
    return this.postProcessItems(items, parsedFormType);
  }

  /**
   * Extract specific items from a filing
   * @param content The filing content
   * @param formType The type of form
   * @param itemNumbers List of item numbers to extract
   * @returns Dictionary with only the requested items
   */
  extractSpecificItems(
    content: string,
    formType: string | FormType,
    itemNumbers: string[]
  ): Record<string, string> {
    const allItems = this.extractItems(content, formType);
    const result: Record<string, string> = {};
    
    for (const itemNum of itemNumbers) {
      if (itemNum in allItems) {
        result[itemNum] = allItems[itemNum];
      }
    }
    
    return result;
  }

  /**
   * Get item definitions for a specific form type
   * @param formType The form type
   * @returns List of item definitions
   */
  getItemDefinitions(formType: string | FormType): ItemDefinition[] {
    const parsedFormType = typeof formType === 'string' ? this.parseFormType(formType) : formType;
    return this.formItems.get(parsedFormType) || [];
  }

  private parseFormType(formTypeStr: string): FormType {
    const upperType = formTypeStr.toUpperCase();

    if (upperType.includes("10-K") || upperType.includes("10K")) {
      return FormType.FORM_10K;
    } else if (upperType.includes("10-Q") || upperType.includes("10Q")) {
      return FormType.FORM_10Q;
    } else if (upperType.includes("8-K") || upperType.includes("8K")) {
      return FormType.FORM_8K;
    } else if (upperType.includes("20-F") || upperType.includes("20F")) {
      return FormType.FORM_20F;
    } else if (upperType.includes("40-F") || upperType.includes("40F")) {
      return FormType.FORM_40F;
    } else {
      throw new InvalidFormTypeError(formTypeStr, ['10-K', '10-Q', '8-K', '20-F', '40-F']);
    }
  }

  private cleanContent(content: string): string {
    // Remove HTML tags but preserve structure
    let cleaned = content.replace(/<[^>]+>/g, ' ');

    // Normalize whitespace
    cleaned = cleaned.replace(/\s+/g, ' ');

    // Preserve line breaks for item boundaries
    cleaned = cleaned.replace(/(Item\s+\d+[A-Z]?\.)/gi, '\n\n$1');

    return cleaned.trim();
  }

  private extractTableOfContents(content: string): Array<[string, number]> {
    const tocItems: Array<[string, number]> = [];

    // Look for table of contents section
    const tocMatch = content.match(
      /TABLE\s+OF\s+CONTENTS(.*?)(?:Item\s+1\.|PART\s+I\s)/is
    );

    if (tocMatch) {
      const tocContent = tocMatch[1];

      // Extract item references from TOC
      const itemPattern = /Item\s+(\d+[A-Z]?)\.\s*([^\n\r.]+)/gi;
      let match;

      while ((match = itemPattern.exec(tocContent)) !== null) {
        const itemNum = match[1].toUpperCase();
        tocItems.push([itemNum, match.index]);
      }
    }

    return tocItems;
  }

  private extractItemsFromContent(
    content: string,
    formType: FormType,
    tocItems: Array<[string, number]>
  ): Map<string, ExtractedItem> {
    const items = new Map<string, ExtractedItem>();
    const itemDefinitions = this.formItems.get(formType) || [];

    for (const itemDef of itemDefinitions) {
      // Build patterns for each item
      const patterns: string[] = [
        `Item\\s+${this.escapeRegex(itemDef.number)}\\.\\s*${this.escapeRegex(itemDef.title)}`,
        `Item\\s+${this.escapeRegex(itemDef.number)}\\.\\s*(?=[A-Z])`,
        `Item\\s+${this.escapeRegex(itemDef.number)}(?:\\.|:|\\s)`,
      ];

      // Add alias patterns
      if (itemDef.aliases) {
        for (const alias of itemDef.aliases) {
          patterns.push(this.escapeRegex(alias));
        }
      }

      // Try each pattern
      for (const pattern of patterns) {
        const regex = new RegExp(pattern, 'gi');
        const matches = Array.from(content.matchAll(regex));

        if (matches.length > 0) {
          // Use the first match after TOC (if TOC exists)
          let match = matches[0];
          
          if (matches.length > 1 && tocItems.length > 0) {
            // Skip matches that appear in TOC
            for (const m of matches.slice(1)) {
              if (!this.isInToc(m.index!, tocItems)) {
                match = m;
                break;
              }
            }
          }

          const startPos = match.index!;

          // Find the end position (start of next item)
          const endPos = this.findItemEnd(content, startPos, itemDefinitions);

          // Extract content
          const itemContent = content.substring(startPos, endPos).trim();

          items.set(itemDef.number, {
            itemNumber: itemDef.number,
            title: itemDef.title,
            content: itemContent,
            startPosition: startPos,
            endPosition: endPos,
          });
          
          break;
        }
      }
    }

    return items;
  }

  private isInToc(position: number, tocItems: Array<[string, number]>): boolean {
    if (tocItems.length === 0) return false;

    // Rough heuristic: if position is before the last TOC item + buffer
    const lastTocPos = Math.max(...tocItems.map(item => item[1]));
    return position < lastTocPos + 500;
  }

  private findItemEnd(
    content: string,
    startPos: number,
    _itemDefinitions: ItemDefinition[]
  ): number {
    // Look for the next item
    const nextItemPattern = /Item\s+\d+[A-Z]?[.:]\s*[A-Z]/i;
    const remainingContent = content.substring(startPos + 10);
    const match = remainingContent.match(nextItemPattern);

    if (match && match.index !== undefined) {
      return startPos + 10 + match.index;
    } else {
      // No next item found, return end of content
      return content.length;
    }
  }

  private postProcessItems(
    items: Map<string, ExtractedItem>,
    _formType: FormType
  ): Record<string, string> {
    const processed: Record<string, string> = {};

    for (const [itemNum, extractedItem] of items) {
      // Clean up the content
      let content = extractedItem.content;

      // Remove excessive whitespace
      content = content.replace(/\n\s*\n\s*\n/g, '\n\n');

      // Ensure we have some content
      if (content.trim().length > 50) {
        processed[itemNum] = content;
      } else {
        // Try to handle empty or placeholder items
        if (content.toLowerCase().includes("none") || 
            content.toLowerCase().includes("not applicable")) {
          processed[itemNum] = content;
        } else {
          processed[itemNum] = "";
        }
      }
    }

    return processed;
  }

  private escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}