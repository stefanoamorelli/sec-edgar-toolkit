/**
 * XBRL instance class providing comprehensive financial data analysis
 */

import { Filing } from '../edgar';
import { EdgarClient } from '../client/edgar-client';
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
  CashFlowItem
} from '../types/xbrl';

export class XBRLInstance {
  private _api: EdgarClient;
  private filing: Filing;
  public readonly cik: string;

  // Cache for XBRL data
  private _facts: XbrlCompanyFacts | null = null;
  private _usGaapFacts: Record<string, any> | null = null;
  private _deiFacts: Record<string, any> | null = null;

  constructor(filing: Filing, api?: EdgarClient) {
    this._api = api || filing.api;
    this.filing = filing;
    this.cik = filing.cik;
  }

  /**
   * Get all XBRL facts for the company
   */
  async getFacts(): Promise<XbrlCompanyFacts> {
    if (!this._facts) {
      this._facts = await this._api.xbrl.getCompanyFacts(this.cik) as XbrlCompanyFacts;
    }
    return this._facts;
  }

  /**
   * Get US-GAAP facts
   */
  async getUsGaap(): Promise<Record<string, any>> {
    if (!this._usGaapFacts) {
      const facts = await this.getFacts();
      this._usGaapFacts = facts?.facts?.['us-gaap'] || {};
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
   * Query XBRL facts with filtering
   */
  async query(options: XbrlQueryOptions = {}): Promise<XbrlFact[]> {
    const {
      concept,
      taxonomy = 'us-gaap',
      unit,
      period
    } = options;

    const results: XbrlFact[] = [];

    // Get facts for the specified taxonomy
    let taxonomyFacts: Record<string, any>;
    if (taxonomy === 'us-gaap') {
      taxonomyFacts = await this.getUsGaap();
    } else if (taxonomy === 'dei') {
      taxonomyFacts = await this.getDei();
    } else {
      const facts = await this.getFacts();
      taxonomyFacts = facts?.facts?.[taxonomy] || {};
    }

    // If concept is specified, filter to that concept
    if (concept) {
      if (concept in taxonomyFacts) {
        const conceptData = taxonomyFacts[concept];
        results.push(...this.processConceptData(concept, conceptData, unit, period));
      }
    } else {
      // Query all concepts
      for (const [conceptName, conceptData] of Object.entries(taxonomyFacts)) {
        results.push(...this.processConceptData(conceptName, conceptData, unit, period));
      }
    }

    return results;
  }

  /**
   * Process concept data and apply filters
   */
  private processConceptData(
    conceptName: string,
    conceptData: any,
    unitFilter?: string,
    periodFilter?: string
  ): XbrlFact[] {
    const results: XbrlFact[] = [];

    const units = conceptData.units || {};
    for (const [unit, unitData] of Object.entries(units)) {
      // Apply unit filter
      if (unitFilter && unit !== unitFilter) {
        continue;
      }

      if (Array.isArray(unitData)) {
        for (const fact of unitData) {
          // Apply period filter
          if (periodFilter) {
            // Check if the filter matches the end date or period fields
            const matchesEndDate = fact.end === periodFilter;
            const matchesInstant = fact.instant === periodFilter;
            const factPeriod = fact.fy || fact.fp || fact.frame || '';
            const matchesPeriod = String(factPeriod).includes(periodFilter);
            
            if (!matchesEndDate && !matchesInstant && !matchesPeriod) {
              continue;
            }
          }

          // Create standardized fact record
          const factRecord: XbrlFact = {
            concept: conceptName,
            taxonomy: 'us-gaap',
            value: fact.val,
            unit: unit,
            period: fact.frame || `FY${fact.fy || ''}${fact.fp || ''}`,
            fiscal_year: fact.fy,
            fiscal_period: fact.fp,
            start_date: fact.start,
            end_date: fact.end,
            filed: fact.filed,
            accession_number: fact.accn,
            form: fact.form,
          };
          results.push(factRecord);
        }
      }
    }

    return results;
  }

  /**
   * Find and extract a specific financial statement
   */
  async findStatement(statementType: string, period?: string): Promise<FinancialStatement | null> {
    switch (statementType) {
      case 'balance_sheet':
        return await this.extractBalanceSheet(period);
      case 'income_statement':
        return await this.extractIncomeStatement(period);
      case 'cash_flow':
        return await this.extractCashFlowStatement(period);
      default:
        console.warn(`Unknown statement type: ${statementType}`);
        return null;
    }
  }

  /**
   * Extract balance sheet data
   */
  private async extractBalanceSheet(period?: string): Promise<FinancialStatement> {
    const concepts = [
      'Assets', 'AssetsCurrent', 'AssetsNoncurrent',
      'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
      'StockholdersEquity', 'RetainedEarningsAccumulatedDeficit'
    ];

    const statementData: Record<string, XbrlFact> = {};
    
    for (const concept of concepts) {
      const facts = await this.query({ concept, unit: 'USD', period });
      if (facts.length > 0) {
        // Get most recent fact
        const latestFact = facts.reduce((prev, current) => 
          (current.filed || '') > (prev.filed || '') ? current : prev
        );
        statementData[concept] = latestFact;
      }
    }

    return {
      statement_type: 'balance_sheet',
      period,
      data: statementData,
    };
  }

  /**
   * Extract income statement data
   */
  private async extractIncomeStatement(period?: string): Promise<FinancialStatement> {
    const concepts = [
      'Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
      'CostOfRevenue', 'GrossProfit',
      'OperatingIncomeLoss', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
      'NetIncomeLoss', 'EarningsPerShareBasic', 'EarningsPerShareDiluted'
    ];

    const statementData: Record<string, XbrlFact> = {};
    
    for (const concept of concepts) {
      const facts = await this.query({ concept, unit: 'USD', period });
      if (facts.length > 0) {
        // Get most recent fact
        const latestFact = facts.reduce((prev, current) => 
          (current.filed || '') > (prev.filed || '') ? current : prev
        );
        statementData[concept] = latestFact;
      }
    }

    return {
      statement_type: 'income_statement',
      period,
      data: statementData,
    };
  }

  /**
   * Extract cash flow statement data
   */
  private async extractCashFlowStatement(period?: string): Promise<FinancialStatement> {
    const concepts = [
      'NetCashProvidedByUsedInOperatingActivities',
      'NetCashProvidedByUsedInInvestingActivities',
      'NetCashProvidedByUsedInFinancingActivities',
      'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'
    ];

    const statementData: Record<string, XbrlFact> = {};
    
    for (const concept of concepts) {
      const facts = await this.query({ concept, unit: 'USD', period });
      if (facts.length > 0) {
        // Get most recent fact
        const latestFact = facts.reduce((prev, current) => 
          (current.filed || '') > (prev.filed || '') ? current : prev
        );
        statementData[concept] = latestFact;
      }
    }

    return {
      statement_type: 'cash_flow',
      period,
      data: statementData,
    };
  }

  /**
   * Get structured balance sheet
   */
  async getBalanceSheet(period?: string): Promise<BalanceSheet> {
    const statement = await this.extractBalanceSheet(period);
    const data = statement.data;

    // Helper to convert XbrlFact to BalanceSheetItem
    const toBalanceSheetItem = (fact: XbrlFact): BalanceSheetItem => ({
      label: fact.concept,
      value: typeof fact.value === 'number' ? fact.value : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || '')
    });

    const assets = {
      current_assets: data.AssetsCurrent ? [toBalanceSheetItem(data.AssetsCurrent)] : [],
      non_current_assets: data.AssetsNoncurrent ? [toBalanceSheetItem(data.AssetsNoncurrent)] : [],
      total_assets: data.Assets ? toBalanceSheetItem(data.Assets) : undefined
    };

    const liabilities = {
      current_liabilities: data.LiabilitiesCurrent ? [toBalanceSheetItem(data.LiabilitiesCurrent)] : [],
      non_current_liabilities: data.LiabilitiesNoncurrent ? [toBalanceSheetItem(data.LiabilitiesNoncurrent)] : [],
      total_liabilities: data.Liabilities ? toBalanceSheetItem(data.Liabilities) : undefined
    };

    const equity = {
      total_equity: data.StockholdersEquity ? toBalanceSheetItem(data.StockholdersEquity) : undefined,
      retained_earnings: data.RetainedEarningsAccumulatedDeficit ? 
        toBalanceSheetItem(data.RetainedEarningsAccumulatedDeficit) : undefined
    };

    return { assets, liabilities, equity };
  }

  /**
   * Get structured income statement
   */
  async getIncomeStatement(period?: string): Promise<IncomeStatement> {
    const statement = await this.extractIncomeStatement(period);
    const data = statement.data;

    // Helper to convert XbrlFact to IncomeStatementItem
    const toIncomeStatementItem = (fact: XbrlFact): IncomeStatementItem => ({
      label: fact.concept,
      value: typeof fact.value === 'number' ? fact.value : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || '')
    });

    return {
      revenue: data.Revenues || data.RevenueFromContractWithCustomerExcludingAssessedTax ? 
        toIncomeStatementItem(data.Revenues || data.RevenueFromContractWithCustomerExcludingAssessedTax) : undefined,
      gross_profit: data.GrossProfit ? toIncomeStatementItem(data.GrossProfit) : undefined,
      operating_income: data.OperatingIncomeLoss ? toIncomeStatementItem(data.OperatingIncomeLoss) : undefined,
      net_income: data.NetIncomeLoss ? toIncomeStatementItem(data.NetIncomeLoss) : undefined,
      earnings_per_share: data.EarningsPerShareBasic ? toIncomeStatementItem(data.EarningsPerShareBasic) : undefined,
      operating_expenses: []
    };
  }

  /**
   * Get structured cash flow statement
   */
  async getCashFlowStatement(period?: string): Promise<CashFlowStatement> {
    const statement = await this.extractCashFlowStatement(period);
    const data = statement.data;

    // Helper to convert XbrlFact to CashFlowItem
    const toCashFlowItem = (fact: XbrlFact): CashFlowItem => ({
      label: fact.concept,
      value: typeof fact.value === 'number' ? fact.value : parseFloat(fact.value as string),
      units: fact.unit,
      period: fact.period,
      filed: new Date(fact.filed || '')
    });

    return {
      operating_activities: data.NetCashProvidedByUsedInOperatingActivities ? 
        [toCashFlowItem(data.NetCashProvidedByUsedInOperatingActivities)] : [],
      investing_activities: data.NetCashProvidedByUsedInInvestingActivities ? 
        [toCashFlowItem(data.NetCashProvidedByUsedInInvestingActivities)] : [],
      financing_activities: data.NetCashProvidedByUsedInFinancingActivities ? 
        [toCashFlowItem(data.NetCashProvidedByUsedInFinancingActivities)] : [],
      net_cash_flow: data.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents ? 
        toCashFlowItem(data.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents) : undefined
    };
  }

  /**
   * Get a single value for a specific concept
   */
  async getConceptValue(
    concept: string,
    taxonomy: string = 'us-gaap',
    unit: string = 'USD',
    period?: string
  ): Promise<number | null> {
    const facts = await this.query({ concept, taxonomy, unit, period });
    if (facts.length > 0) {
      // Return the most recent value
      const latestFact = facts.reduce((prev, current) => 
        (current.filed || '') > (prev.filed || '') ? current : prev
      );
      return typeof latestFact.value === 'number' ? 
        latestFact.value : parseFloat(latestFact.value as string);
    }
    return null;
  }

  /**
   * Get all facts for a specific concept
   */
  async getFactsByConcept(concept: string, taxonomy: string = 'us-gaap'): Promise<XbrlFact[]> {
    const facts = await this.getFacts();
    const taxonomyFacts = facts?.facts?.[taxonomy];
    
    if (!taxonomyFacts || !taxonomyFacts[concept]) {
      return [];
    }
    
    const conceptData = taxonomyFacts[concept];
    const results: XbrlFact[] = [];
    
    // Process all units
    for (const [unit, values] of Object.entries(conceptData.units || {})) {
      if (Array.isArray(values)) {
        for (const value of values) {
          results.push({
            concept,
            taxonomy,
            value: value.val,
            unit,
            period: value.end || value.instant || '',
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
  async listConcepts(taxonomy: string = 'us-gaap'): Promise<string[]> {
    let taxonomyFacts: Record<string, any>;
    
    if (taxonomy === 'us-gaap') {
      taxonomyFacts = await this.getUsGaap();
    } else if (taxonomy === 'dei') {
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