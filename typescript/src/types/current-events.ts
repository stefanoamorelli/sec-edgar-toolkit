/**
 * Type definitions for 8-K current events parsing
 */

export interface Event {
  type: string;
  description: string;
  date: Date;
  item: string;
  significance: 'low' | 'medium' | 'high';
  details: Record<string, any>;
}

export interface Agreement {
  type: string;
  parties: string[];
  effectiveDate: Date;
  description: string;
  value: number | null;
  currency: string;
}

export interface ExecutiveChange {
  type: 'appointment' | 'resignation' | 'termination';
  person: {
    name: string;
    position: string;
    previousPosition?: string;
  };
  effectiveDate: Date;
  reason?: string;
  compensation?: {
    salary: number;
    bonus: number;
    equity: number;
  };
}

export interface Acquisition {
  type: 'acquisition' | 'merger' | 'divestiture';
  target: {
    name: string;
    description: string;
  };
  value: number | null;
  currency: string;
  expectedClosingDate: Date | null;
  status: 'announced' | 'pending' | 'completed' | 'terminated';
}

export interface EarningsData {
  period: string;
  revenue: number | null;
  netIncome: number | null;
  earningsPerShare: number | null;
  guidance: {
    metric: string;
    value: string;
  }[];
}

export interface ParsedCurrentEvent {
  formType: string;
  filingDate: Date;
  cik: string;
  companyName: string;
  ticker: string;
  events: Event[];
  materialAgreements: Agreement[];
  executiveChanges: ExecutiveChange[];
  acquisitions: Acquisition[];
  earningsResults: EarningsData | null;
}