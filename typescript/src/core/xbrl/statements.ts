/**
 * Statement definitions: canonical names, aliases, and concept lists used
 * to assemble statement snapshots from company facts.
 */

export const STATEMENT_ALIASES: Record<string, string> = {
  balancesheet: "balance_sheet",
  consolidatedbalancesheets: "balance_sheet",
  incomestatement: "income_statement",
  statementsofincome: "income_statement",
  consolidatedstatementsofoperations: "income_statement",
  cashflow: "cash_flow",
  consolidatedstatementsofcashflows: "cash_flow",
};

export const STATEMENT_CONCEPTS: Record<string, string[]> = {
  balance_sheet: [
    "Assets",
    "AssetsCurrent",
    "AssetsNoncurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "LiabilitiesNoncurrent",
    "StockholdersEquity",
    "RetainedEarningsAccumulatedDeficit",
  ],
  income_statement: [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfRevenue",
    "GrossProfit",
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
  ],
  cash_flow: [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
  ],
};

/** Map free-form statement names ("BalanceSheet") to canonical keys. */
export function normalizeStatementType(statementType: string): string {
  const normalized = statementType.trim().toLowerCase().replace(/[\s_]/g, "");
  return (
    STATEMENT_ALIASES[normalized] ||
    (statementType.includes("_") ? statementType : normalized)
  );
}
