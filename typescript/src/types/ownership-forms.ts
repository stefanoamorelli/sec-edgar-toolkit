/**
 * Type definitions for SEC ownership forms (Forms 3, 4, and 5)
 */

export interface DocumentInfo {
  formType: string;
  schemaVersion: string;
  documentType: string;
  periodOfReport: Date | null;
  dateOfOriginalSubmission: Date | null;
  notSubjectToSection16?: boolean;
}

export interface IssuerInfo {
  cik: string;
  name: string;
  tradingSymbol: string;
}

export interface OwnerRelationship {
  isDirector: boolean;
  isOfficer: boolean;
  isTenPercentOwner: boolean;
  isOther: boolean;
  officerTitle: string;
  otherText: string;
}

export interface ReportingOwnerInfo {
  cik: string;
  name: string;
  street1: string;
  street2: string;
  city: string;
  state: string;
  zipCode: string;
  stateDescription: string;
  relationship?: OwnerRelationship;
}

export interface NonDerivativeTransaction {
  securityTitle: string;
  transactionDate: Date | null;
  shares: number;
  pricePerShare: number;
  acquiredDisposedCode: string;
  formType?: string;
  code?: string;
  equitySwapInvolved?: boolean;
  sharesOwnedFollowingTransaction?: number;
  directOrIndirectOwnership?: string;
  natureOfOwnership?: string;
}

export interface NonDerivativeHolding {
  securityTitle: string;
  sharesOwned: number;
  directOrIndirectOwnership: string;
  natureOfOwnership?: string;
}

export interface UnderlyingSecurity {
  title: string;
  shares: number;
}

export interface DerivativeTransaction {
  securityTitle: string;
  conversionOrExercisePrice: number;
  transactionDate: Date | null;
  shares: number;
  totalValue: number;
  acquiredDisposedCode: string;
  exerciseDate?: Date | null;
  expirationDate?: Date | null;
  underlyingSecurity?: UnderlyingSecurity;
}

export interface ParsedOwnershipForm {
  documentInfo: DocumentInfo;
  issuerInfo: IssuerInfo;
  reportingOwnerInfo: ReportingOwnerInfo;
  nonDerivativeTransactions: NonDerivativeTransaction[];
  nonDerivativeHoldings: NonDerivativeHolding[];
  derivativeTransactions: DerivativeTransaction[];
}

export class OwnershipFormParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'OwnershipFormParseError';
  }
}