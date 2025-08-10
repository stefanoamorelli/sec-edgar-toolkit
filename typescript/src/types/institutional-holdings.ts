/**
 * Type definitions for 13F institutional holdings parsing
 */

export interface Holding {
  nameOfIssuer: string;
  titleOfClass: string;
  cusip: string;
  value: number;
  sharesOrPrincipalAmount: {
    shares: number;
    principal: number;
    type: 'SH' | 'PRN';
  };
  putCall: 'Put' | 'Call' | null;
  investmentDiscretion: 'SOLE' | 'SHARED' | 'NONE';
  managerClass: string;
  votingAuthority: {
    sole: number;
    shared: number;
    none: number;
  };
}

export interface PortfolioSummary {
  totalValue: number;
  totalPositions: number;
  topSectorAllocation: string;
  concentrationRatio: number;
  averagePositionSize: number;
}

export interface Position {
  holding: Holding;
  portfolioWeight: number;
  rank: number;
}

export interface SectorAllocation {
  sector: string;
  value: number;
  percentage: number;
  numberOfHoldings: number;
}

export interface HoldingComparison {
  holding: string;
  cusip: string;
  previousValue: number;
  currentValue: number;
  changeInValue: number;
  changeInShares: number;
  action: 'NEW' | 'SOLD_OUT' | 'INCREASED' | 'DECREASED' | 'NO_CHANGE';
}

export interface ParsedInstitutionalHolding {
  formType: string;
  filingDate: Date;
  periodOfReport: Date;
  cik: string;
  managerName: string;
  holdings: Holding[];
  portfolioSummary: PortfolioSummary;
  sectorAllocations: SectorAllocation[];
}