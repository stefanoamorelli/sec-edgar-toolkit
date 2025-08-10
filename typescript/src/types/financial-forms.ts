/**
 * Type definitions for financial forms (10-K, 10-Q) parsing
 */

export interface BalanceSheetItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface BalanceSheet {
  assets: {
    currentAssets: BalanceSheetItem[];
    nonCurrentAssets: BalanceSheetItem[];
    totalAssets: BalanceSheetItem | null;
  };
  liabilities: {
    currentLiabilities: BalanceSheetItem[];
    nonCurrentLiabilities: BalanceSheetItem[];
    totalLiabilities: BalanceSheetItem | null;
  };
  equity: {
    totalEquity: BalanceSheetItem | null;
    retainedEarnings: BalanceSheetItem | null;
  };
}

export interface IncomeStatementItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface IncomeStatement {
  revenue: IncomeStatementItem | null;
  grossProfit: IncomeStatementItem | null;
  operatingIncome: IncomeStatementItem | null;
  netIncome: IncomeStatementItem | null;
  earningsPerShare: IncomeStatementItem | null;
  operatingExpenses: IncomeStatementItem[];
}

export interface CashFlowItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface CashFlowStatement {
  operatingActivities: CashFlowItem[];
  investingActivities: CashFlowItem[];
  financingActivities: CashFlowItem[];
  netCashFlow: CashFlowItem | null;
}

export interface BusinessSegment {
  name: string;
  revenue: number;
  operatingIncome: number;
  assets: number;
  description: string;
}

export interface RiskFactor {
  category: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export interface MDSection {
  title: string;
  content: string;
  keyMetrics: Array<{
    metric: string;
    value: string;
    change: string;
  }>;
}

export interface XBRLFact {
  name: string;
  value: number | string;
  units: string;
  contextRef: string;
  decimals: number;
  period: string;
}

export interface FinancialMetrics {
  marketCap: number | null;
  peRatio: number | null;
  debtToEquity: number | null;
  returnOnEquity: number | null;
  currentRatio: number | null;
  quickRatio: number | null;
}

export interface ParsedFinancialForm {
  formType: string;
  filingDate: Date;
  periodEndDate: Date;
  cik: string;
  companyName: string;
  ticker: string;
  balanceSheet: BalanceSheet;
  incomeStatement: IncomeStatement;
  cashFlowStatement: CashFlowStatement;
  businessSegments: BusinessSegment[];
  riskFactors: RiskFactor[];
  managementDiscussion: MDSection[];
  xbrlFacts: XBRLFact[];
  financialMetrics: FinancialMetrics;
}