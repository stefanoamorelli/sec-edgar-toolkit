/**
 * Type definitions for DEF 14A proxy statements parsing
 */

export interface CompensationItem {
  year: number;
  salary: number;
  bonus: number;
  stockAwards: number;
  optionAwards: number;
  nonEquityIncentive: number;
  changeInPension: number;
  otherCompensation: number;
  total: number;
}

export interface CompensationTable {
  name: string;
  position: string;
  compensation: CompensationItem[];
}

export interface CompensationSummary {
  totalCompensation: number;
  medianCompensation: number;
  ceoPayRatio: number;
  topExecutives: Array<{
    name: string;
    position: string;
    totalCompensation: number;
  }>;
}

export interface BoardMember {
  name: string;
  position: string;
  tenure: number;
  age: number;
  independence: boolean;
  committees: string[];
  otherDirectorships: string[];
  compensation: number;
}

export interface Proposal {
  number: number;
  title: string;
  description: string;
  type: 'management' | 'shareholder';
  recommendation: 'for' | 'against' | 'abstain';
  details: string;
}

export interface VotingMatter {
  proposal: Proposal;
  votesFor: number;
  votesAgainst: number;
  abstentions: number;
  brokerNonVotes: number;
  outcome: 'passed' | 'failed' | 'pending';
}

export interface ParsedProxyStatement {
  formType: string;
  filingDate: Date;
  meetingDate: Date;
  cik: string;
  companyName: string;
  ticker: string;
  executiveCompensation: CompensationTable[];
  compensationSummary: CompensationSummary;
  boardMembers: BoardMember[];
  proposals: Proposal[];
  votingMatters: VotingMatter[];
}