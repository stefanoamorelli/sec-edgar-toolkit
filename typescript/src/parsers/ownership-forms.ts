/**
 * Parser for SEC ownership forms (Form 3, 4, and 5) XML documents.
 *
 * These forms contain information about insider transactions and holdings
 * by officers, directors, and significant shareholders.
 *
 * Form 3: Initial statement of beneficial ownership
 * Form 4: Changes in beneficial ownership
 * Form 5: Annual statement of changes in beneficial ownership
 */

import { XMLParser } from 'fast-xml-parser';
import {
  DocumentInfo,
  IssuerInfo,
  ReportingOwnerInfo,
  NonDerivativeTransaction,
  NonDerivativeHolding,
  DerivativeTransaction,
  ParsedOwnershipForm,
  OwnershipFormParseError,
} from '../types/ownership-forms';

export { OwnershipFormParseError };

export class OwnershipFormParser {
  private xmlContent: string | Buffer;
  private root: any;
  public readonly formType: string;

  /**
   * Initialize the ownership form parser.
   * @param xmlContent Raw XML content of the form
   * @throws OwnershipFormParseError If XML parsing fails
   */
  constructor(xmlContent: string | Buffer) {
    this.xmlContent = xmlContent;
    
    try {
      const parser = new XMLParser({
        ignoreAttributes: false,
        parseTagValue: false, // Don't auto-parse numbers to preserve leading zeros
        trimValues: true,
      });
      
      const xmlString = typeof xmlContent === 'string' 
        ? xmlContent 
        : xmlContent.toString('utf-8');
      
      this.root = parser.parse(xmlString);
    } catch (error: any) {
      throw new OwnershipFormParseError(`Failed to parse XML: ${error.message}`);
    }

    this.formType = this.extractFormType();
    console.info(`Initialized parser for Form ${this.formType}`);
  }

  /**
   * Extract the form type from the XML document.
   */
  private extractFormType(): string {
    // Navigate through possible wrapper elements
    const doc = this.root.ownershipDocument || this.root;
    
    // Try multiple possible locations for form type
    const documentType = this.findNestedValue(doc, ['documentType']);
    if (documentType) {
      return documentType.toString().trim();
    }

    // Fallback: check schemaVersion or other indicators
    const schemaVersion = this.findNestedValue(doc, ['schemaVersion']);
    if (schemaVersion) {
      // Assume it's a Form 4 if we can't find explicit type
      return '4';
    }

    throw new OwnershipFormParseError('Could not determine form type from XML');
  }

  /**
   * Find a nested value in the XML structure
   */
  private findNestedValue(obj: any, path: string[]): any {
    let current = obj;
    
    for (const key of path) {
      if (!current) return null;
      
      // Direct property
      if (current[key] !== undefined) {
        current = current[key];
        continue;
      }
      
      // Search in all properties (case insensitive)
      let found = false;
      for (const prop in current) {
        if (prop.toLowerCase() === key.toLowerCase()) {
          current = current[prop];
          found = true;
          break;
        }
      }
      
      if (!found) return null;
    }
    
    return current;
  }

  /**
   * Safely extract text from an XML element.
   */
  private getText(element: any, defaultValue: string = ''): string {
    if (!element) return defaultValue;
    
    if (typeof element === 'string' || typeof element === 'number') {
      return element.toString().trim();
    }
    
    if (element.value !== undefined) {
      return this.getText(element.value, defaultValue);
    }
    
    if (element['#text'] !== undefined) {
      return element['#text'].toString().trim();
    }
    
    return defaultValue;
  }

  /**
   * Safely extract float value from an XML element.
   */
  private getFloat(element: any, defaultValue: number = 0.0): number {
    const text = this.getText(element);
    if (!text) return defaultValue;
    
    const parsed = parseFloat(text);
    return isNaN(parsed) ? defaultValue : parsed;
  }

  /**
   * Extract date from XML element and convert to Date object.
   */
  private getDate(element: any): Date | null {
    const dateText = this.getText(element);
    if (!dateText) return null;

    // Try different date formats
    const dateFormats = [
      /^\d{4}-\d{2}-\d{2}$/, // 2024-01-15
      /^\d{1,2}\/\d{1,2}\/\d{4}$/, // 01/15/2024 or 1/15/2024
      /^\d{1,2}-\d{1,2}-\d{4}$/, // 01-15-2024 or 1-15-2024
    ];

    // Check which format matches
    if (dateFormats[0].test(dateText)) {
      return new Date(dateText);
    } else if (dateFormats[1].test(dateText)) {
      const [month, day, year] = dateText.split('/');
      return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    } else if (dateFormats[2].test(dateText)) {
      const [month, day, year] = dateText.split('-');
      return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    }

    console.warn(`Could not parse date: ${dateText}`);
    return null;
  }

  /**
   * Parse document-level information from the form.
   */
  parseDocumentInfo(): DocumentInfo {
    const doc = this.root.ownershipDocument || this.root;
    
    const periodOfReport = this.findNestedValue(doc, ['periodOfReport']);
    const dateOfOriginalSubmission = this.findNestedValue(doc, ['dateOfOriginalSubmission']);
    const notSubjectToSection16 = this.findNestedValue(doc, ['notSubjectToSection16']);

    return {
      formType: this.formType,
      schemaVersion: this.getText(this.findNestedValue(doc, ['schemaVersion'])),
      documentType: this.getText(this.findNestedValue(doc, ['documentType'])),
      periodOfReport: this.getDate(periodOfReport),
      dateOfOriginalSubmission: this.getDate(dateOfOriginalSubmission),
      ...(notSubjectToSection16 !== null && {
        notSubjectToSection16: this.getText(notSubjectToSection16).toLowerCase() === 'true'
      })
    };
  }

  /**
   * Parse information about the issuer (company) from the form.
   */
  parseIssuerInfo(): IssuerInfo {
    const doc = this.root.ownershipDocument || this.root;
    const issuer = this.findNestedValue(doc, ['issuer']);
    
    if (!issuer) {
      return { cik: '', name: '', tradingSymbol: '' };
    }

    return {
      cik: this.getText(issuer.issuerCik || ''),
      name: this.getText(issuer.issuerName || ''),
      tradingSymbol: this.getText(issuer.issuerTradingSymbol || ''),
    };
  }

  /**
   * Parse information about the reporting owner (insider) from the form.
   */
  parseReportingOwnerInfo(): ReportingOwnerInfo {
    const doc = this.root.ownershipDocument || this.root;
    const reportingOwner = this.findNestedValue(doc, ['reportingOwner']);
    
    if (!reportingOwner) {
      return {
        cik: '',
        name: '',
        street1: '',
        street2: '',
        city: '',
        state: '',
        zipCode: '',
        stateDescription: '',
      };
    }

    const ownerInfo: ReportingOwnerInfo = {
      cik: '',
      name: '',
      street1: '',
      street2: '',
      city: '',
      state: '',
      zipCode: '',
      stateDescription: '',
    };

    // Parse owner identification
    const ownerId = reportingOwner.reportingOwnerId;
    if (ownerId) {
      ownerInfo.cik = this.getText(ownerId.rptOwnerCik || '');
      ownerInfo.name = this.getText(ownerId.rptOwnerName || '');
      ownerInfo.street1 = this.getText(ownerId.rptOwnerStreet1 || '');
      ownerInfo.street2 = this.getText(ownerId.rptOwnerStreet2 || '');
      ownerInfo.city = this.getText(ownerId.rptOwnerCity || '');
      ownerInfo.state = this.getText(ownerId.rptOwnerState || '');
      ownerInfo.zipCode = this.getText(ownerId.rptOwnerZipCode || '');
      ownerInfo.stateDescription = this.getText(ownerId.rptOwnerStateDescription || '');
    }

    // Parse owner relationship
    const relationship = reportingOwner.reportingOwnerRelationship;
    if (relationship) {
      ownerInfo.relationship = {
        isDirector: this.getText(relationship.isDirector || '').toLowerCase() === 'true',
        isOfficer: this.getText(relationship.isOfficer || '').toLowerCase() === 'true',
        isTenPercentOwner: this.getText(relationship.isTenPercentOwner || '').toLowerCase() === 'true',
        isOther: this.getText(relationship.isOther || '').toLowerCase() === 'true',
        officerTitle: this.getText(relationship.officerTitle || ''),
        otherText: this.getText(relationship.otherText || ''),
      };
    }

    return ownerInfo;
  }

  /**
   * Parse non-derivative transactions from the form.
   */
  parseNonDerivativeTransactions(): NonDerivativeTransaction[] {
    const doc = this.root.ownershipDocument || this.root;
    
    // Look for transactions in nonDerivativeTable or directly in the document
    const nonDerivativeTable = this.findNestedValue(doc, ['nonDerivativeTable']);
    let transactionElements;
    
    if (nonDerivativeTable) {
      transactionElements = nonDerivativeTable.nonDerivativeTransaction || [];
    } else {
      // Try to find transactions directly in the document
      transactionElements = doc.nonDerivativeTransaction || [];
    }
    
    const transactions: NonDerivativeTransaction[] = [];
    const transactionArray = Array.isArray(transactionElements) ? transactionElements : [transactionElements];

    for (const transElem of transactionArray) {
      if (!transElem) continue;

      const transaction: NonDerivativeTransaction = {
        securityTitle: '',
        transactionDate: null,
        shares: 0,
        pricePerShare: 0,
        acquiredDisposedCode: '',
      };

      // Security title
      const security = transElem.securityTitle;
      if (security) {
        transaction.securityTitle = this.getText(security.value || security);
      }

      // Transaction date
      const transDate = transElem.transactionDate;
      if (transDate) {
        transaction.transactionDate = this.getDate(transDate.value || transDate);
      }

      // Transaction amounts
      const amounts = transElem.transactionAmounts;
      if (amounts) {
        transaction.shares = this.getFloat(amounts.transactionShares?.value || amounts.transactionShares);
        transaction.pricePerShare = this.getFloat(amounts.transactionPricePerShare?.value || amounts.transactionPricePerShare);
        transaction.acquiredDisposedCode = this.getText(amounts.transactionAcquiredDisposedCode?.value || amounts.transactionAcquiredDisposedCode);
      }

      // Transaction coding
      const coding = transElem.transactionCoding;
      if (coding) {
        transaction.formType = this.getText(coding.transactionFormType);
        transaction.code = this.getText(coding.transactionCode);
        transaction.equitySwapInvolved = this.getText(coding.equitySwapInvolved).toLowerCase() === 'true';
      }

      // Post-transaction amounts
      const postTrans = transElem.postTransactionAmounts;
      if (postTrans) {
        transaction.sharesOwnedFollowingTransaction = this.getFloat(
          postTrans.sharesOwnedFollowingTransaction?.value || postTrans.sharesOwnedFollowingTransaction
        );
        transaction.directOrIndirectOwnership = this.getText(
          postTrans.directOrIndirectOwnership?.value || postTrans.directOrIndirectOwnership
        );
      }

      // Ownership nature
      const ownership = transElem.ownershipNature;
      if (ownership) {
        transaction.natureOfOwnership = this.getText(ownership.value || ownership);
      }

      transactions.push(transaction);
    }

    return transactions;
  }

  /**
   * Parse non-derivative holdings from the form.
   */
  parseNonDerivativeHoldings(): NonDerivativeHolding[] {
    const doc = this.root.ownershipDocument || this.root;
    const nonDerivativeTable = this.findNestedValue(doc, ['nonDerivativeTable']);
    
    if (!nonDerivativeTable) return [];

    const holdings: NonDerivativeHolding[] = [];
    const holdingElements = nonDerivativeTable.nonDerivativeHolding || [];
    const holdingArray = Array.isArray(holdingElements) ? holdingElements : [holdingElements];

    for (const holdingElem of holdingArray) {
      if (!holdingElem) continue;

      const holding: NonDerivativeHolding = {
        securityTitle: '',
        sharesOwned: 0,
        directOrIndirectOwnership: '',
      };

      // Security title
      const security = holdingElem.securityTitle;
      if (security) {
        holding.securityTitle = this.getText(security.value || security);
      }

      // Shares owned
      const shares = holdingElem.sharesOwned;
      if (shares) {
        holding.sharesOwned = this.getFloat(shares.value || shares);
      }

      // Direct or indirect ownership
      const ownershipType = holdingElem.directOrIndirectOwnership;
      if (ownershipType) {
        holding.directOrIndirectOwnership = this.getText(ownershipType.value || ownershipType);
      }

      // Nature of ownership
      const nature = holdingElem.ownershipNature;
      if (nature) {
        holding.natureOfOwnership = this.getText(nature.value || nature);
      }

      holdings.push(holding);
    }

    return holdings;
  }

  /**
   * Parse derivative transactions (options, warrants, etc.) from the form.
   */
  parseDerivativeTransactions(): DerivativeTransaction[] {
    const doc = this.root.ownershipDocument || this.root;
    const derivativeTable = this.findNestedValue(doc, ['derivativeTable']);
    
    if (!derivativeTable) return [];

    const transactions: DerivativeTransaction[] = [];
    const transactionElements = derivativeTable.derivativeTransaction || [];
    const transactionArray = Array.isArray(transactionElements) ? transactionElements : [transactionElements];

    for (const transElem of transactionArray) {
      if (!transElem) continue;

      const transaction: DerivativeTransaction = {
        securityTitle: '',
        conversionOrExercisePrice: 0,
        transactionDate: null,
        shares: 0,
        totalValue: 0,
        acquiredDisposedCode: '',
      };

      // Security title
      const security = transElem.securityTitle;
      if (security) {
        transaction.securityTitle = this.getText(security.value || security);
      }

      // Conversion or exercise price
      const conversion = transElem.conversionOrExercisePrice;
      if (conversion) {
        transaction.conversionOrExercisePrice = this.getFloat(conversion.value || conversion);
      }

      // Transaction date
      const transDate = transElem.transactionDate;
      if (transDate) {
        transaction.transactionDate = this.getDate(transDate.value || transDate);
      }

      // Transaction amounts
      const amounts = transElem.transactionAmounts;
      if (amounts) {
        transaction.shares = this.getFloat(amounts.transactionShares?.value || amounts.transactionShares);
        transaction.totalValue = this.getFloat(amounts.transactionTotalValue?.value || amounts.transactionTotalValue);
        transaction.acquiredDisposedCode = this.getText(amounts.transactionAcquiredDisposedCode?.value || amounts.transactionAcquiredDisposedCode);
      }

      // Exercise date and expiration date
      const exerciseDate = transElem.exerciseDate;
      if (exerciseDate) {
        transaction.exerciseDate = this.getDate(exerciseDate.value || exerciseDate);
      }

      const expirationDate = transElem.expirationDate;
      if (expirationDate) {
        transaction.expirationDate = this.getDate(expirationDate.value || expirationDate);
      }

      // Underlying security
      const underlying = transElem.underlyingSecurity;
      if (underlying) {
        transaction.underlyingSecurity = {
          title: this.getText(underlying.underlyingSecurityTitle?.value || underlying.underlyingSecurityTitle || ''),
          shares: this.getFloat(underlying.underlyingSecurityShares?.value || underlying.underlyingSecurityShares),
        };
      }

      transactions.push(transaction);
    }

    return transactions;
  }

  /**
   * Parse all information from the ownership form.
   */
  parseAll(): ParsedOwnershipForm {
    return {
      documentInfo: this.parseDocumentInfo(),
      issuerInfo: this.parseIssuerInfo(),
      reportingOwnerInfo: this.parseReportingOwnerInfo(),
      nonDerivativeTransactions: this.parseNonDerivativeTransactions(),
      nonDerivativeHoldings: this.parseNonDerivativeHoldings(),
      derivativeTransactions: this.parseDerivativeTransactions(),
    };
  }
}

/**
 * Specialized parser for Form 4 (Changes in Beneficial Ownership).
 * Form 4 must be filed within 2 business days of a transaction.
 */
export class Form4Parser extends OwnershipFormParser {
  constructor(xmlContent: string | Buffer) {
    super(xmlContent);
    const form = this.parseDocumentInfo();
    if (form.formType !== '4') {
      console.warn(`Expected Form 4, but found Form ${form.formType}`);
    }
  }
}

/**
 * Specialized parser for Form 5 (Annual Statement of Changes in Beneficial Ownership).
 * Form 5 is filed annually and reports transactions that were exempt from
 * Form 4 reporting requirements.
 */
export class Form5Parser extends OwnershipFormParser {
  constructor(xmlContent: string | Buffer) {
    super(xmlContent);
    const form = this.parseDocumentInfo();
    if (form.formType !== '5') {
      console.warn(`Expected Form 5, but found Form ${form.formType}`);
    }
  }
}