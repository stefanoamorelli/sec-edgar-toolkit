/**
 * Type definitions for cross-form analytics
 */

export interface TimelineEvent {
  date: Date;
  type: 'filing' | 'insider_transaction' | 'institutional_change' | 'earnings' | 'announcement';
  formType: string;
  description: string;
  significance: 'low' | 'medium' | 'high';
  details: Record<string, any>;
}

export interface Timeline {
  cik: string;
  companyName: string;
  events: TimelineEvent[];
  period: {
    start: Date;
    end: Date;
  };
}

export interface Correlation {
  type: 'insider_trading_vs_earnings' | 'insider_trading_vs_announcements' | 'institutional_vs_performance';
  strength: number;
  significance: number;
  description: string;
  dataPoints: Array<{
    date: Date;
    value1: number;
    value2: number;
  }>;
}

export interface OwnershipChange {
  period: string;
  institutionalOwnership: {
    previous: number;
    current: number;
    change: number;
  };
  insiderOwnership: {
    previous: number;
    current: number;
    change: number;
  };
  majorShareholders: Array<{
    name: string;
    type: 'institutional' | 'insider' | 'other';
    ownership: number;
    change: number;
  }>;
}

export interface OwnershipTrend {
  cik: string;
  companyName: string;
  changes: OwnershipChange[];
  trends: {
    institutionalTrend: 'increasing' | 'decreasing' | 'stable';
    insiderTrend: 'increasing' | 'decreasing' | 'stable';
    concentration: 'increasing' | 'decreasing' | 'stable';
  };
}

export interface ComplianceMetrics {
  cik: string;
  companyName: string;
  period: {
    start: Date;
    end: Date;
  };
  filingCompliance: {
    onTime: number;
    late: number;
    missed: number;
    score: number;
  };
  insiderCompliance: {
    form4OnTime: number;
    form4Late: number;
    form5Filed: number;
    score: number;
  };
  overallScore: number;
  riskLevel: 'low' | 'medium' | 'high';
}