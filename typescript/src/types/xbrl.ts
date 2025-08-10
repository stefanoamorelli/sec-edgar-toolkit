/**
 * XBRL type definitions
 */

export interface XbrlFact {
  concept: string;
  taxonomy: string;
  value: number | string;
  unit: string;
  period: string;
  fiscal_year?: number;
  fiscal_period?: string;
  start_date?: string;
  end_date?: string;
  filed?: string;
  accession_number?: string;
  form?: string;
}

export interface BalanceSheetItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface BalanceSheetAssets {
  current_assets: BalanceSheetItem[];
  non_current_assets: BalanceSheetItem[];
  total_assets?: BalanceSheetItem;
}

export interface BalanceSheetLiabilities {
  current_liabilities: BalanceSheetItem[];
  non_current_liabilities: BalanceSheetItem[];
  total_liabilities?: BalanceSheetItem;
}

export interface BalanceSheetEquity {
  total_equity?: BalanceSheetItem;
  retained_earnings?: BalanceSheetItem;
}

export interface BalanceSheet {
  assets: BalanceSheetAssets;
  liabilities: BalanceSheetLiabilities;
  equity: BalanceSheetEquity;
}

export interface IncomeStatementItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface IncomeStatement {
  revenue?: IncomeStatementItem;
  gross_profit?: IncomeStatementItem;
  operating_income?: IncomeStatementItem;
  net_income?: IncomeStatementItem;
  earnings_per_share?: IncomeStatementItem;
  operating_expenses: IncomeStatementItem[];
}

export interface CashFlowItem {
  label: string;
  value: number;
  units: string;
  period: string;
  filed: Date;
}

export interface CashFlowStatement {
  operating_activities: CashFlowItem[];
  investing_activities: CashFlowItem[];
  financing_activities: CashFlowItem[];
  net_cash_flow?: CashFlowItem;
}

export interface FinancialStatement {
  statement_type: 'balance_sheet' | 'income_statement' | 'cash_flow';
  period?: string;
  data: Record<string, XbrlFact>;
}

export interface XbrlInstanceOptions {
  filing: any; // Will be properly typed when Filing is imported
  api?: any; // Will be properly typed when SecEdgarApi is imported
}

export interface XbrlQueryOptions {
  concept?: string;
  taxonomy?: string;
  unit?: string;
  period?: string;
}

export interface XbrlCompanyFacts {
  cik: string;
  entityName: string;
  facts: {
    'us-gaap'?: Record<string, any>;
    'dei'?: Record<string, any>;
    [taxonomy: string]: Record<string, any> | undefined;
  };
}