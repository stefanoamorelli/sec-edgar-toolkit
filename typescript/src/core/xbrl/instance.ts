/**
 * XBRL instance of the high-level API.
 *
 * `XBRLInstance` composes two data sources for one filing:
 *
 * - fact-level queries served from the company-facts API (`queries`), and
 * - filing-scoped statement structure parsed from the filing's rendered
 *   reports (`rendered-reports`), including dimensional detail such as
 *   segment breakdowns.
 */

import {
  XbrlFact,
  XbrlCompanyFacts,
  XbrlQueryOptions,
  FinancialStatement,
  BalanceSheet,
  IncomeStatement,
  CashFlowStatement,
  BalanceSheetItem,
  IncomeStatementItem,
  CashFlowItem,
} from "../../types/xbrl";
import {
  buildFactRecords,
  factsHistory,
  parseFilterExpression,
  FactHistoryRow,
  FactQuery,
} from "./queries";
import { AsReportedStatements } from "./as-reported";
import { RenderedReportReader, ReportDescriptor } from "./rendered-reports";
import { StatementLineItem } from "./report-html-parser";
import { STATEMENT_CONCEPTS, normalizeStatementType } from "./statements";

/** The pieces of a filing (fluent or object API) the instance needs. */
export interface XbrlFilingLike {
  cik: string;
  accessionNumber?: string;
  formType?: string;
  filingDate?: string | Date;
  api?: XbrlApiLike;
}

/** The pieces of the API client the instance needs. */
export interface XbrlApiLike {
  xbrl: { getCompanyFacts(cik: string | number): Promise<Record<string, any>> };
  httpClient?: { getRaw(url: string): Promise<string> };
  getFiling?(
    cik: string | number,
    accessionNumber: string,
  ): Promise<Record<string, any>>;
}

export class XBRLInstance {
  private _api: XbrlApiLike;
  private filing: XbrlFilingLike;
  public readonly cik: string;

  // Cache for XBRL data
  private _facts: XbrlCompanyFacts | null = null;
  private _usGaapFacts: Record<string, any> | null = null;
  private _deiFacts: Record<string, any> | null = null;
  private _reportsReader: RenderedReportReader | null = null;
  private _asReported: AsReportedStatements | null = null;

  constructor(filing: XbrlFilingLike, api?: XbrlApiLike) {
    const resolvedApi = api || filing.api;
    if (!resolvedApi) {
      throw new Error("XBRLInstance requires an API client");
    }
    this._api = resolvedApi;
    this.filing = filing;
    this.cik = filing.cik;
  }

  private get archiveBase(): string {
    const accession = (this.filing.accessionNumber || "").replace(/-/g, "");
    return `https://www.sec.gov/Archives/edgar/data/${parseInt(this.cik, 10)}/${accession}`;
  }

  /** Reader for the filing's rendered reports. */
  get reports(): RenderedReportReader {
    if (!this._reportsReader) {
      const http = this._api.httpClient;
      if (!http) {
        throw new Error("Rendered-report access requires an HTTP client");
      }
      this._reportsReader = new RenderedReportReader(this.archiveBase, http);
    }
    return this._reportsReader;
  }

  /**
   * Statements assembled from the filing's own XBRL fileset
   * (instance document plus presentation and label linkbases).
   */
  async asReported(): Promise<AsReportedStatements> {
    if (!this._asReported) {
      const fileNames: string[] = [];
      if (this._api.getFiling && this.filing.accessionNumber) {
        try {
          const details = await this._api.getFiling(
            this.cik,
            this.filing.accessionNumber,
          );
          for (const item of details?.directory?.item || []) {
            if (item?.name) {
              fileNames.push(String(item.name));
            }
          }
        } catch {
          // fall through with an empty listing
        }
      }
      const http = this._api.httpClient;
      if (!http) {
        throw new Error("As-reported access requires an HTTP client");
      }
      this._asReported = new AsReportedStatements(
        this.archiveBase,
        http,
        fileNames,
      );
    }
    return this._asReported;
  }

  /** The parsed XBRL instance document, or null when absent. */
  async instanceDocument() {
    return (await this.asReported()).getDocument();
  }

  /**
   * Get all XBRL facts for the company
   */
  async getFacts(): Promise<XbrlCompanyFacts> {
    if (!this._facts) {
      this._facts = (await this._api.xbrl.getCompanyFacts(
        this.cik,
      )) as XbrlCompanyFacts;
    }
    return this._facts;
  }

  /**
   * Get US-GAAP facts
   */
  async getUsGaap(): Promise<Record<string, any>> {
    if (!this._usGaapFacts) {
      const facts = await this.getFacts();
      this._usGaapFacts = facts?.facts?.["us-gaap"] || {};
    }
    return this._usGaapFacts;
  }

  /**
   * Get DEI (Document Entity Information) facts
   */
  async getDei(): Promise<Record<string, any>> {
    if (!this._deiFacts) {
      const facts = await this.getFacts();
      this._deiFacts = facts?.facts?.dei || {};
    }
    return this._deiFacts;
  }

  /**
   * Query XBRL facts with filtering.
   *
   * Accepts an options object (`{ concept: 'Assets', unit: 'USD' }`) or a
   * filter expression string (`"concept=Assets&unit=USD"`; the empty
   * string selects everything). Returns a FactQuery (an array with a
   * chainable `byConcept()` helper).
   */
  async query(options: XbrlQueryOptions | string = {}): Promise<FactQuery> {
    if (typeof options === "string") {
      options = options === "" ? {} : parseFilterExpression(options);
    }
    const { concept, taxonomy = "us-gaap", unit, period } = options;

    const results: XbrlFact[] = [];

    // Get facts for the specified taxonomy
    let taxonomyFacts: Record<string, any>;
    if (taxonomy === "us-gaap") {
      taxonomyFacts = await this.getUsGaap();
    } else if (taxonomy === "dei") {
      taxonomyFacts = await this.getDei();
    } else {
      const facts = await this.getFacts();
      taxonomyFacts = facts?.facts?.[taxonomy] || {};
    }

    if (concept) {
      if (concept in taxonomyFacts) {
        results.push(
          ...buildFactRecords(
            concept,
            taxonomyFacts[concept],
            taxonomy,
            unit,
            period,
          ),
        );
      }
    } else {
      for (const [conceptName, conceptData] of Object.entries(taxonomyFacts)) {
        results.push(
          ...buildFactRecords(conceptName, conceptData, taxonomy, unit, period),
        );
      }
    }

    return FactQuery.fromRecords(results);
  }

  /** History of one concept, sorted by period end ascending. */
  async factsHistory(
    concept: string,
    taxonomy: string = "us-gaap",
  ): Promise<FactHistoryRow[]> {
    const facts = await this.getFacts();
    return factsHistory(facts as Record<string, any>, concept, taxonomy);
  }

  // ------------------------------------------------------------------
  // Filing-scoped statements (rendered reports)
  // ------------------------------------------------------------------

  /**
   * List all rendered reports in the filing, with `definition`,
   * `shortName`, `role`, and `rFile` keys.
   */
  async getAllStatements(): Promise<ReportDescriptor[]> {
    const rendered = await this.reports.listReports();
    if (rendered.length > 0) {
      return rendered;
    }
    // No FilingSummary (the renderer never ran for this filing):
    // fall back to the roles defined by the presentation linkbase.
    const asReported = await this.asReported();
    if (asReported.isAvailable) {
      const roles = await asReported.listRoles();
      return roles.map((role) => ({
        definition: role.split("/").pop() || role,
        shortName: role.split("/").pop() || role,
        role,
        rFile: "",
        reportType: "",
      }));
    }
    return rendered;
  }

  /**
   * Parse one rendered report into line items.
   *
   * @param role The report's role URI (from `getAllStatements()`), its
   *   R-file name, or its short name.
   */
  async getStatement(
    role: string,
    source: "auto" | "instance" | "rendered" = "auto",
  ): Promise<StatementLineItem[]> {
    if (source !== "rendered") {
      const asReported = await this.asReported();
      if (asReported.isAvailable) {
        let resolved = role;
        if (role.toLowerCase().endsWith(".htm")) {
          const report = await this.reports.findReport(role);
          if (report) {
            resolved = report.role;
          }
        }
        const items = await asReported.getStatement(resolved);
        if (items.length > 0 || source === "instance") {
          return items;
        }
      }
      if (source === "instance") {
        return [];
      }
    }
    return this.reports.readStatement(role);
  }

  /**
   * Find and extract a specific financial statement.
   *
   * Accepts "balance_sheet" / "income_statement" / "cash_flow" and
   * common CamelCase spellings ("BalanceSheet").
   */
  async findStatement(
    statementType: string,
    period?: string,
  ): Promise<FinancialStatement | null> {
    const normalized = normalizeStatementType(statementType);
    const concepts = STATEMENT_CONCEPTS[normalized];
    if (!concepts) {
      return null;
    }
    return this.extractStatementFromFacts(normalized, concepts, period);
  }

  private async extractStatementFromFacts(
    statementType: string,
    concepts: string[],
    period?: string,
  ): Promise<FinancialStatement> {
    const statementData: Record<string, XbrlFact> = {};

    for (const concept of concepts) {
      let facts = await this.query({ concept, unit: "USD", period });
      if (facts.length === 0) {
        facts = await this.query({ concept, period });
      }
      if (facts.length > 0) {
        const latestFact = facts.reduce((prev, current) =>
          (current.filed || "") > (prev.filed || "") ? current : prev,
        );
        statementData[concept] = latestFact;
      }
    }

    return {
      statement_type: statementType as FinancialStatement["statement_type"],
      period,
      data: statementData,
    };
  }

  /**
   * Get structured balance sheet
   */
  async getBalanceSheet(period?: string): Promise<BalanceSheet> {
    const statement = await this.findStatement("balance_sheet", period);
    const data = statement?.data || {};

    const toBalanceSheetItem = (fact: XbrlFact): BalanceSheetItem => ({
      label: fact.concept,
      value:
        typeof fact.value === "number"
          ? fact.value
          : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || ""),
    });

    const assets = {
      current_assets: data.AssetsCurrent
        ? [toBalanceSheetItem(data.AssetsCurrent)]
        : [],
      non_current_assets: data.AssetsNoncurrent
        ? [toBalanceSheetItem(data.AssetsNoncurrent)]
        : [],
      total_assets: data.Assets ? toBalanceSheetItem(data.Assets) : undefined,
    };

    const liabilities = {
      current_liabilities: data.LiabilitiesCurrent
        ? [toBalanceSheetItem(data.LiabilitiesCurrent)]
        : [],
      non_current_liabilities: data.LiabilitiesNoncurrent
        ? [toBalanceSheetItem(data.LiabilitiesNoncurrent)]
        : [],
      total_liabilities: data.Liabilities
        ? toBalanceSheetItem(data.Liabilities)
        : undefined,
    };

    const equity = {
      total_equity: data.StockholdersEquity
        ? toBalanceSheetItem(data.StockholdersEquity)
        : undefined,
      retained_earnings: data.RetainedEarningsAccumulatedDeficit
        ? toBalanceSheetItem(data.RetainedEarningsAccumulatedDeficit)
        : undefined,
    };

    return { assets, liabilities, equity };
  }

  /**
   * Get structured income statement
   */
  async getIncomeStatement(period?: string): Promise<IncomeStatement> {
    const statement = await this.findStatement("income_statement", period);
    const data = statement?.data || {};

    const toIncomeStatementItem = (fact: XbrlFact): IncomeStatementItem => ({
      label: fact.concept,
      value:
        typeof fact.value === "number"
          ? fact.value
          : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || ""),
    });

    return {
      revenue:
        data.Revenues ||
        data.RevenueFromContractWithCustomerExcludingAssessedTax
          ? toIncomeStatementItem(
              data.Revenues ||
                data.RevenueFromContractWithCustomerExcludingAssessedTax,
            )
          : undefined,
      gross_profit: data.GrossProfit
        ? toIncomeStatementItem(data.GrossProfit)
        : undefined,
      operating_income: data.OperatingIncomeLoss
        ? toIncomeStatementItem(data.OperatingIncomeLoss)
        : undefined,
      net_income: data.NetIncomeLoss
        ? toIncomeStatementItem(data.NetIncomeLoss)
        : undefined,
      earnings_per_share: data.EarningsPerShareBasic
        ? toIncomeStatementItem(data.EarningsPerShareBasic)
        : undefined,
      operating_expenses: [],
    };
  }

  /**
   * Get structured cash flow statement
   */
  async getCashFlowStatement(period?: string): Promise<CashFlowStatement> {
    const statement = await this.findStatement("cash_flow", period);
    const data = statement?.data || {};

    const toCashFlowItem = (fact: XbrlFact): CashFlowItem => ({
      label: fact.concept,
      value:
        typeof fact.value === "number"
          ? fact.value
          : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || ""),
    });

    return {
      operating_activities: data.NetCashProvidedByUsedInOperatingActivities
        ? [toCashFlowItem(data.NetCashProvidedByUsedInOperatingActivities)]
        : [],
      investing_activities: data.NetCashProvidedByUsedInInvestingActivities
        ? [toCashFlowItem(data.NetCashProvidedByUsedInInvestingActivities)]
        : [],
      financing_activities: data.NetCashProvidedByUsedInFinancingActivities
        ? [toCashFlowItem(data.NetCashProvidedByUsedInFinancingActivities)]
        : [],
      net_cash_flow:
        data.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
          ? toCashFlowItem(
              data.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents,
            )
          : undefined,
    };
  }

  /**
   * Get a single value for a specific concept
   */
  async getConceptValue(
    concept: string,
    taxonomy: string = "us-gaap",
    unit: string = "USD",
    period?: string,
  ): Promise<number | null> {
    const facts = await this.query({ concept, taxonomy, unit, period });
    if (facts.length > 0) {
      const latestFact = facts.reduce((prev, current) =>
        (current.filed || "") > (prev.filed || "") ? current : prev,
      );
      return typeof latestFact.value === "number"
        ? latestFact.value
        : parseFloat(latestFact.value as string);
    }
    return null;
  }

  /**
   * Get all facts for a specific concept
   */
  async getFactsByConcept(
    concept: string,
    taxonomy: string = "us-gaap",
  ): Promise<XbrlFact[]> {
    const facts = await this.getFacts();
    const taxonomyFacts = facts?.facts?.[taxonomy];

    if (!taxonomyFacts || !taxonomyFacts[concept]) {
      return [];
    }

    const conceptData = taxonomyFacts[concept];
    const results: XbrlFact[] = [];

    // Dated periods (end/instant), unlike query()'s fiscal-frame periods
    for (const [unit, values] of Object.entries(conceptData.units || {})) {
      if (Array.isArray(values)) {
        for (const value of values) {
          results.push({
            concept,
            taxonomy,
            value: value.val,
            unit,
            period: value.end || value.instant || "",
            fiscal_year: value.fy,
            fiscal_period: value.fp,
            start_date: value.start,
            end_date: value.end,
            filed: value.filed,
            accession_number: value.accn,
            form: value.form,
          });
        }
      }
    }

    return results;
  }

  /**
   * List all available concepts in a taxonomy
   */
  async listConcepts(taxonomy: string = "us-gaap"): Promise<string[]> {
    let taxonomyFacts: Record<string, any>;

    if (taxonomy === "us-gaap") {
      taxonomyFacts = await this.getUsGaap();
    } else if (taxonomy === "dei") {
      taxonomyFacts = await this.getDei();
    } else {
      const facts = await this.getFacts();
      taxonomyFacts = facts?.facts?.[taxonomy] || {};
    }

    return Object.keys(taxonomyFacts);
  }

  /**
   * Convert XBRL data to plain object
   */
  async toObject(options: XbrlQueryOptions = {}): Promise<any> {
    const facts = await this.query(options);
    return {
      metadata: {
        cik: this.cik,
        filing_date: this.filing.filingDate,
        form_type: this.filing.formType,
      },
      facts: facts,
    };
  }

  toString(): string {
    return `XBRL instance for ${this.filing.formType} filing (CIK: ${this.cik})`;
  }
}
