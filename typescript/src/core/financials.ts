/**
 * Financial statements built from XBRL company facts.
 *
 * `Financials.extract(filing)` builds statement views for one filing;
 * `incomeStatement()` / `balanceSheet()` / `cashFlow()` return a
 * `StatementTable` (rows = concepts, columns = period end dates).
 *
 * The data source is the company-facts API filtered to the filing's form
 * type, which yields as-reported values for the periods the filing covers.
 */

export const INCOME_STATEMENT_CONCEPTS = [
  "Revenues",
  "RevenueFromContractWithCustomerExcludingAssessedTax",
  "CostOfRevenue",
  "CostOfGoodsAndServicesSold",
  "GrossProfit",
  "ResearchAndDevelopmentExpense",
  "SellingGeneralAndAdministrativeExpense",
  "OperatingExpenses",
  "OperatingIncomeLoss",
  "NonoperatingIncomeExpense",
  "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
  "IncomeTaxExpenseBenefit",
  "NetIncomeLoss",
  "EarningsPerShareBasic",
  "EarningsPerShareDiluted",
];

export const BALANCE_SHEET_CONCEPTS = [
  "CashAndCashEquivalentsAtCarryingValue",
  "MarketableSecuritiesCurrent",
  "AccountsReceivableNetCurrent",
  "InventoryNet",
  "AssetsCurrent",
  "PropertyPlantAndEquipmentNet",
  "Goodwill",
  "MarketableSecuritiesNoncurrent",
  "AssetsNoncurrent",
  "Assets",
  "AccountsPayableCurrent",
  "LiabilitiesCurrent",
  "LongTermDebtNoncurrent",
  "LiabilitiesNoncurrent",
  "Liabilities",
  "CommonStocksIncludingAdditionalPaidInCapital",
  "RetainedEarningsAccumulatedDeficit",
  "StockholdersEquity",
];

export const CASH_FLOW_CONCEPTS = [
  "NetCashProvidedByUsedInOperatingActivities",
  "NetCashProvidedByUsedInInvestingActivities",
  "NetCashProvidedByUsedInFinancingActivities",
  "PaymentsToAcquirePropertyPlantAndEquipment",
  "PaymentsOfDividends",
  "PaymentsForRepurchaseOfCommonStock",
  "DepreciationDepletionAndAmortization",
  "ShareBasedCompensation",
  "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
];

export interface StatementRow {
  concept: string;
  /** period end date (ISO) -> reported value */
  values: Record<string, number | null>;
}

export interface StatementTable {
  /** Period end dates (ISO), most recent first. */
  periods: string[];
  rows: StatementRow[];
}

interface FilingLike {
  cik: string;
  formType?: string;
  accessionNumber?: string;
  api: { getCompanyFacts(cik: string): Promise<Record<string, any>> };
}

export class Financials {
  private readonly facts: Record<string, any>;
  public readonly formType: string;
  public readonly accessionNumber?: string;

  constructor(
    factsData: Record<string, any>,
    formType: string = "10-K",
    accessionNumber?: string,
  ) {
    this.facts = (factsData || {}).facts || factsData || {};
    this.formType = formType;
    this.accessionNumber = accessionNumber;
  }

  /** Build Financials for a Filing (high-level entry point). */
  static async extract(filing: FilingLike): Promise<Financials> {
    const raw = await filing.api.getCompanyFacts(filing.cik);
    return new Financials(
      raw,
      filing.formType || "10-K",
      filing.accessionNumber,
    );
  }

  private collect(concepts: string[]): StatementTable {
    const gaap = this.facts["us-gaap"] || {};
    const annual = this.formType.toUpperCase().startsWith("10-K");

    // concept -> { end date -> value }
    const table = new Map<string, Record<string, number>>();
    for (const concept of concepts) {
      const conceptData = gaap[concept];
      if (!conceptData) {
        continue;
      }
      for (const unitFacts of Object.values(conceptData.units || {})) {
        if (!Array.isArray(unitFacts)) {
          continue;
        }
        const series: Record<string, number> = {};
        for (const fact of unitFacts) {
          const form = fact.form || "";
          if (annual && form !== "10-K") {
            continue;
          }
          if (!annual && form !== "10-Q" && form !== "10-K") {
            continue;
          }
          if (annual && fact.fp != null && fact.fp !== "FY") {
            continue;
          }
          if (!fact.end) {
            continue;
          }
          // Later entries are later-filed values for the same period
          series[fact.end] = fact.val;
        }
        if (Object.keys(series).length > 0) {
          table.set(concept, series);
          break; // first unit with data wins (USD before shares)
        }
      }
    }

    if (table.size === 0) {
      return { periods: [], rows: [] };
    }

    const allPeriods = new Set<string>();
    for (const series of table.values()) {
      for (const period of Object.keys(series)) {
        allPeriods.add(period);
      }
    }
    const periods = Array.from(allPeriods).sort().reverse().slice(0, 4);

    const rows: StatementRow[] = [];
    for (const [concept, series] of table) {
      const values: Record<string, number | null> = {};
      let hasValue = false;
      for (const period of periods) {
        const value = series[period];
        values[period] = value ?? null;
        if (value != null) {
          hasValue = true;
        }
      }
      if (hasValue) {
        rows.push({ concept, values });
      }
    }

    return { periods, rows };
  }

  incomeStatement(): StatementTable {
    return this.collect(INCOME_STATEMENT_CONCEPTS);
  }

  balanceSheet(): StatementTable {
    return this.collect(BALANCE_SHEET_CONCEPTS);
  }

  cashFlow(): StatementTable {
    return this.collect(CASH_FLOW_CONCEPTS);
  }

  cashFlowStatement(): StatementTable {
    return this.cashFlow();
  }
}
