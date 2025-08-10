/**
 * Parser for 8-K current events documents.
 */

import {
  ParsedCurrentEvent,
  Event,
  Agreement,
  ExecutiveChange,
  Acquisition,
  EarningsData,
} from '../types';

export class CurrentEventParser {
  private rawContent: string;

  constructor(rawContent: string) {
    this.rawContent = rawContent;
  }

  /**
   * Parse all current events from the 8-K filing
   */
  parseAll(): ParsedCurrentEvent {
    const header = this.parseHeader();
    
    return {
      formType: header.formType,
      filingDate: header.filingDate,
      cik: header.cik,
      companyName: header.companyName,
      ticker: header.ticker,
      events: this.getCurrentEvents(),
      materialAgreements: this.getMaterialAgreements(),
      executiveChanges: this.getExecutiveChanges(),
      acquisitions: this.getAcquisitions(),
      earningsResults: this.getEarningsResults(),
    };
  }

  /**
   * Extract current events from the filing
   */
  getCurrentEvents(): Event[] {
    const events: Event[] = [];
    
    // Extract Item numbers and descriptions
    const itemPattern = /Item\s+(\d+\.\d+)\.?\s+([^\n\r]+)/gi;
    let match;
    
    while ((match = itemPattern.exec(this.rawContent)) !== null) {
      const itemNumber = match[1];
      const description = match[2].trim();
      
      events.push({
        type: this.mapItemToEventType(itemNumber),
        description: description,
        date: this.extractFilingDate(),
        item: `Item ${itemNumber}`,
        significance: this.assessEventSignificance(description),
        details: {
          itemNumber: itemNumber,
          fullText: this.extractItemContent(itemNumber),
        },
      });
    }

    return events;
  }

  /**
   * Extract material agreements
   */
  getMaterialAgreements(): Agreement[] {
    const agreements: Agreement[] = [];
    
    // Look for agreement-related content
    const agreementSection = this.extractSection('ITEM 1.01|MATERIAL AGREEMENT|DEFINITIVE AGREEMENT');
    
    if (agreementSection) {
      // Extract the company name (from the filing)
      const companyMatch = this.rawContent.match(/(?:^|\n)([A-Z][A-Z\s]+(?:INC\.|CORP\.|CORPORATION|COMPANY|LLC))(?:\s|\n)/m);
      const companyName = companyMatch ? companyMatch[1].trim() : 'Unknown Company';
      
      // Extract agreement type - skip the item header
      const contentAfterHeader = agreementSection.replace(/^ITEM\s+\d+\.\d+[^\n\r]*[\n\r]+/i, '');
      const typeMatch = contentAfterHeader.match(/(?:entered into|executed|signed)\s+(?:a|an|the)?\s*([A-Za-z\s]+Agreement)/i);
      const agreementType = typeMatch ? typeMatch[1].trim() : 'Material Agreement';
      
      // Find counterparty
      const withPattern = /(?:with|between.*?and)\s+([A-Za-z\s]+(?:Inc\.|Corp\.|Technologies|Company|LLC)?)[\s,.(]/i;
      const withMatch = agreementSection.match(withPattern);
      const counterparty = withMatch ? withMatch[1].trim() : '';
      
      const parties = [companyName];
      if (counterparty && !counterparty.toLowerCase().includes('the company')) {
        parties.push(counterparty);
      }
      
      // Try to extract the date from the agreement text
      const dateMatch = contentAfterHeader.match(/On\s+([A-Za-z]+ \d+, \d+)/);
      const effectiveDate = dateMatch ? new Date(dateMatch[1]) : this.extractFilingDate();
      
      agreements.push({
        type: agreementType,
        parties: parties,
        effectiveDate: effectiveDate,
        description: agreementSection.substring(0, 500),
        value: this.extractAgreementValue(agreementSection),
        currency: 'USD',
      });
    }

    return agreements;
  }

  /**
   * Extract executive changes
   */
  getExecutiveChanges(): ExecutiveChange[] {
    const changes: ExecutiveChange[] = [];
    
    // Look for executive change content
    const changeSection = this.extractSection('ITEM 5.02|DEPARTURE.*DIRECTOR|APPOINTMENT.*OFFICER');
    
    if (changeSection) {
      // Look for departures/resignations
      const departurePattern = /(?:\(b\))\s*On\s+[A-Za-z]+ \d+, \d+,\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),.*?(?:notified|informed|announced|resignation|retire|departure)/gi;
      let match;
      
      while ((match = departurePattern.exec(changeSection)) !== null) {
        const name = match[1].trim();
        const position = this.extractPosition(changeSection, name);
        const effectiveDate = this.extractDateAfterName(changeSection, name);
        
        changes.push({
          type: 'resignation',
          person: {
            name: name,
            position: position,
          },
          effectiveDate: effectiveDate || this.extractFilingDate(),
        });
      }
      
      // Look for appointments
      const appointmentPattern = /(?:appointed|named)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:,|\s+as|\s+to)/gi;
      
      while ((match = appointmentPattern.exec(changeSection)) !== null) {
        const name = match[1].trim();
        const position = this.extractPosition(changeSection, name);
        const effectiveDate = this.extractDateAfterName(changeSection, name);
        
        changes.push({
          type: 'appointment',
          person: {
            name: name,
            position: position,
          },
          effectiveDate: effectiveDate || this.extractFilingDate(),
        });
      }
    }

    return changes;
  }

  /**
   * Extract acquisitions and mergers
   */
  getAcquisitions(): Acquisition[] {
    const acquisitions: Acquisition[] = [];
    
    // Look for acquisition content
    const acquisitionSection = this.extractSection('ITEM 2.01|ACQUISITION|MERGER|DIVESTITURE');
    
    if (acquisitionSection) {
      acquisitions.push({
        type: 'acquisition',
        target: {
          name: this.extractTargetName(acquisitionSection),
          description: acquisitionSection.substring(0, 300),
        },
        value: this.extractTransactionValue(acquisitionSection),
        currency: 'USD',
        expectedClosingDate: null,
        status: 'announced',
      });
    }

    return acquisitions;
  }

  /**
   * Extract earnings results
   */
  getEarningsResults(): EarningsData | null {
    // Look for earnings-related content
    const earningsSection = this.extractSection('ITEM 2.02|RESULTS.*OPERATIONS|EARNINGS');
    
    if (!earningsSection) {
      return null;
    }

    return {
      period: this.extractReportingPeriod(),
      revenue: this.extractMetric(earningsSection, 'revenue|sales'),
      netIncome: this.extractMetric(earningsSection, 'net income|earnings'),
      earningsPerShare: this.extractMetric(earningsSection, 'earnings per share|EPS'),
      guidance: this.extractGuidance(earningsSection),
    };
  }

  // Helper methods

  private parseHeader() {
    const cikMatch = this.rawContent.match(/CENTRAL INDEX KEY:\s*(\d+)/);
    const companyMatch = this.rawContent.match(/COMPANY CONFORMED NAME:\s*([^\n\r]+)/);
    const formTypeMatch = this.rawContent.match(/FORM TYPE:\s*([^\n\r]+)/);
    const filingDateMatch = this.rawContent.match(/FILED AS OF DATE:\s*(\d{8})/);
    
    return {
      cik: cikMatch?.[1] || '',
      companyName: companyMatch?.[1]?.trim() || '',
      formType: formTypeMatch?.[1]?.trim() || '',
      ticker: '', // Would need to extract from trading symbol
      filingDate: this.parseDate(filingDateMatch?.[1]),
    };
  }

  private extractSection(pattern: string): string {
    const regex = new RegExp(pattern, 'i');
    const match = this.rawContent.match(regex);
    if (!match) return '';
    
    const startIndex = match.index || 0;
    // Look for next Item (case-insensitive)
    const nextItemMatch = this.rawContent.substring(startIndex + 1).match(/Item\s+\d+\.\d+/i);
    const endIndex = nextItemMatch ? startIndex + 1 + (nextItemMatch.index || 0) : -1;
    
    return this.rawContent.substring(startIndex, endIndex > 0 ? endIndex : startIndex + 10000);
  }

  private mapItemToEventType(itemNumber: string): string {
    const itemMap: Record<string, string> = {
      '1.01': 'Material Agreement',
      '1.02': 'Termination of Material Agreement',
      '2.01': 'Acquisition or Disposition',
      '2.02': 'Results of Operations',
      '3.01': 'Notice of Delisting',
      '5.02': 'Executive Changes',
      '8.01': 'Other Events',
    };
    
    return itemMap[itemNumber] || 'Other Event';
  }

  private assessEventSignificance(description: string): 'low' | 'medium' | 'high' {
    const highKeywords = ['acquisition', 'merger', 'bankruptcy', 'material adverse'];
    const mediumKeywords = ['agreement', 'executive', 'earnings', 'results'];
    
    const text = description.toLowerCase();
    
    if (highKeywords.some(keyword => text.includes(keyword))) {
      return 'high';
    } else if (mediumKeywords.some(keyword => text.includes(keyword))) {
      return 'medium';
    }
    
    return 'low';
  }

  private extractItemContent(itemNumber: string): string {
    const escapedNumber = itemNumber.replace('.', '\\.');
    const itemPattern = new RegExp(`Item\\s+${escapedNumber}\\s+[^\\n\\r]+`, 'gi');
    const match = this.rawContent.match(itemPattern);
    if (!match) return '';
    
    // Just return first 10 words for brevity
    const words = match[0].split(/\s+/);
    return words.slice(0, 10).join(' ');
  }

  private extractFilingDate(): Date {
    const dateMatch = this.rawContent.match(/FILED AS OF DATE:\s*(\d{8})/);
    return this.parseDate(dateMatch?.[1]);
  }

  private parseDate(dateStr?: string): Date {
    if (!dateStr) return new Date();
    
    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1;
    const day = parseInt(dateStr.substring(6, 8));
    
    return new Date(year, month, day);
  }

  private extractAgreementValue(text: string): number | null {
    const valuePattern = /\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?/i;
    const match = text.match(valuePattern);
    
    if (match) {
      let value = parseFloat(match[1].replace(/,/g, ''));
      if (text.toLowerCase().includes('million')) {
        value *= 1000000;
      } else if (text.toLowerCase().includes('billion')) {
        value *= 1000000000;
      }
      return value;
    }
    
    return null;
  }

  private extractPosition(text: string, name: string): string {
    // Replace newlines with spaces for easier matching
    const cleanText = text.replace(/\n/g, ' ').replace(/\s+/g, ' ');
    
    // Check if this is an appointment (contains "appointed" before the name)
    const isAppointment = cleanText.toLowerCase().indexOf('appointed') < cleanText.indexOf(name) && 
                          cleanText.toLowerCase().indexOf('appointed') > -1;
    
    // Look for patterns that include the full position title
    const patterns = isAppointment ? [
      // For appointments: "Jane Doe, age 45, as the new Senior Vice President..."
      new RegExp(`${name}(?:,\\s*age\\s*\\d+,)?.*?as\\s+(?:the\\s+)?(?:new\\s+)?([^,\\.]+?)(?:,|\\seffective|\\.)`, 'i'),
    ] : [
      // For departures: "John Smith, Senior Vice President..."
      new RegExp(`${name},\\s*([^,]+?)\\s*(?:,|notified|informed|announced)`, 'i'),
      // "Senior Vice President John Smith"
      new RegExp(`([^,]*(?:Vice President|President|Director|Officer|Manager)[^,]*),?\\s*${name}`, 'i')
    ];
    
    for (const pattern of patterns) {
      const match = cleanText.match(pattern);
      if (match && match[1]) {
        const position = match[1].trim();
        // Only return if it looks like a complete position
        if (position.length > 5 && position.match(/\w+\s+\w+/)) {
          return position;
        }
      }
    }
    
    // Fallback
    return 'Executive';
  }

  private extractTargetName(text: string): string {
    const targetPattern = /(?:acquire|purchase|merger with)\s+([A-Z][^,.]{10,50})/i;
    const match = text.match(targetPattern);
    return match?.[1]?.trim() || 'Target Company';
  }

  private extractTransactionValue(text: string): number | null {
    return this.extractAgreementValue(text);
  }

  private extractReportingPeriod(): string {
    // Look for explicit period mention in earnings section
    const periodMatch = this.rawContent.match(/(?:quarter|period|year)\s+ended\s+([A-Za-z]+ \d+, \d+)/i);
    if (periodMatch) {
      return periodMatch[1];
    }
    
    const conformedPeriodMatch = this.rawContent.match(/CONFORMED PERIOD OF REPORT:\s*(\d{8})/);
    if (conformedPeriodMatch) {
      const date = this.parseDate(conformedPeriodMatch[1]);
      return `Q${Math.ceil((date.getMonth() + 1) / 3)} ${date.getFullYear()}`;
    }
    return 'Current Period';
  }

  private extractMetric(text: string, pattern: string): number | null {
    // Try different formats for monetary values
    const patterns = [
      new RegExp(`(?:${pattern}).*?\\$([0-9,]+(?:\\.[0-9]+)?)\\s*billion`, 'i'),
      new RegExp(`(?:${pattern}).*?\\$([0-9,]+(?:\\.[0-9]+)?)\\s*million`, 'i'),
      new RegExp(`(?:${pattern}).*?\\$([0-9,]+(?:\\.[0-9]+)?)`, 'i'),
      new RegExp(`(?:${pattern}).*?([0-9,]+(?:\\.[0-9]+)?)\\s*billion`, 'i'),
      new RegExp(`(?:${pattern}).*?([0-9,]+(?:\\.[0-9]+)?)\\s*million`, 'i')
    ];
    
    const multipliers = {
      billion: 1000000000,
      million: 1000000,
      default: 1
    };
    
    for (const patternRegex of patterns) {
      const match = text.match(patternRegex);
      if (match && match[1]) {
        const value = parseFloat(match[1].replace(/,/g, ''));
        const matchStr = match[0].toLowerCase();
        
        if (matchStr.includes('billion')) {
          return value * multipliers.billion;
        } else if (matchStr.includes('million')) {
          return value * multipliers.million;
        } else {
          return value;
        }
      }
    }
    
    return null;
  }

  private extractGuidance(text: string): Array<{ metric: string; value: string }> {
    const guidance: Array<{ metric: string; value: string }> = [];
    
    const guidancePattern = /(?:guidance|expects?).*?([a-zA-Z\s]+).*?(\$[0-9,]+|\d+%)/gi;
    let match;
    
    while ((match = guidancePattern.exec(text)) !== null) {
      guidance.push({
        metric: match[1].trim(),
        value: match[2],
      });
    }
    
    return guidance;
  }
  
  private extractDateAfterName(text: string, name: string): Date | null {
    // Look for "effective [date]" pattern after the name
    const patterns = [
      new RegExp(`effective\\s+([A-Za-z]+ \\d+, \\d+)`, 'i'),
      new RegExp(`retire.*?effective\\s+([A-Za-z]+ \\d+, \\d+)`, 'i'),
      new RegExp(`resignation.*?effective\\s+([A-Za-z]+ \\d+, \\d+)`, 'i'),
    ];
    
    // Find the position of the name
    const nameIndex = text.indexOf(name);
    if (nameIndex === -1) return null;
    
    // Search for date pattern after the name
    const textAfterName = text.substring(nameIndex);
    
    for (const pattern of patterns) {
      const match = textAfterName.match(pattern);
      if (match && match[1]) {
        return new Date(match[1]);
      }
    }
    
    return null;
  }
}