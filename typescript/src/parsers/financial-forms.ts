/**
 * Parser for financial forms (10-K, 10-Q) documents.
 */

import {
  ParsedFinancialForm,
  BalanceSheet,
  IncomeStatement,
  CashFlowStatement,
  BusinessSegment,
  RiskFactor,
  MDSection,
  XBRLFact,
  FinancialMetrics,
  BalanceSheetItem,
  IncomeStatementItem,
  CashFlowItem,
  ParsedDocument,
} from '../types';

export class FinancialFormParser {
  private rawContent: string;
  private document: ParsedDocument | null = null;

  constructor(rawContent: string) {
    this.rawContent = rawContent;
  }

  /**
   * Parse financial statements from the filing
   */
  getFinancialStatements(): {
    balanceSheet: BalanceSheet;
    incomeStatement: IncomeStatement;
    cashFlowStatement: CashFlowStatement;
  } {
    return {
      balanceSheet: this.parseBalanceSheet(),
      incomeStatement: this.parseIncomeStatement(),
      cashFlowStatement: this.parseCashFlowStatement(),
    };
  }

  /**
   * Parse balance sheet data
   */
  parseBalanceSheet(): BalanceSheet {
    const balanceSheetSection = this.extractSection('BALANCE SHEET|CONSOLIDATED BALANCE SHEET');
    
    return {
      assets: {
        currentAssets: this.extractBalanceSheetItems(balanceSheetSection, 'current.*assets'),
        nonCurrentAssets: this.extractBalanceSheetItems(balanceSheetSection, 'non.?current.*assets|property.*plant.*equipment'),
        totalAssets: this.extractBalanceSheetItem(balanceSheetSection, 'total.*assets'),
      },
      liabilities: {
        currentLiabilities: this.extractBalanceSheetItems(balanceSheetSection, 'current.*liabilities'),
        nonCurrentLiabilities: this.extractBalanceSheetItems(balanceSheetSection, 'non.?current.*liabilities|long.?term.*debt'),
        totalLiabilities: this.extractBalanceSheetItem(balanceSheetSection, 'total.*liabilities'),
      },
      equity: {
        totalEquity: this.extractBalanceSheetItem(balanceSheetSection, 'total.*equity|shareholders.*equity'),
        retainedEarnings: this.extractBalanceSheetItem(balanceSheetSection, 'retained.*earnings'),
      },
    };
  }

  /**
   * Parse income statement data
   */
  parseIncomeStatement(): IncomeStatement {
    const incomeSection = this.extractSection('INCOME STATEMENT|CONSOLIDATED STATEMENT.*OPERATIONS|STATEMENT.*EARNINGS');
    
    return {
      revenue: this.extractIncomeStatementItem(incomeSection, 'revenue|net.*sales|total.*revenue'),
      grossProfit: this.extractIncomeStatementItem(incomeSection, 'gross.*profit|gross.*margin'),
      operatingIncome: this.extractIncomeStatementItem(incomeSection, 'operating.*income|income.*from.*operations'),
      netIncome: this.extractIncomeStatementItem(incomeSection, 'net.*income|net.*earnings'),
      earningsPerShare: this.extractIncomeStatementItem(incomeSection, 'earnings.*per.*share|basic.*earnings.*per.*share'),
      operatingExpenses: this.extractIncomeStatementItems(incomeSection, 'operating.*expenses|research.*development|sales.*marketing'),
    };
  }

  /**
   * Parse cash flow statement data
   */
  parseCashFlowStatement(): CashFlowStatement {
    const cashFlowSection = this.extractSection('CASH FLOW|CONSOLIDATED STATEMENT.*CASH.*FLOW');
    
    return {
      operatingActivities: this.extractCashFlowItems(cashFlowSection, 'operating.*activities|cash.*from.*operations'),
      investingActivities: this.extractCashFlowItems(cashFlowSection, 'investing.*activities|cash.*from.*investing'),
      financingActivities: this.extractCashFlowItems(cashFlowSection, 'financing.*activities|cash.*from.*financing'),
      netCashFlow: this.extractCashFlowItem(cashFlowSection, 'net.*cash.*flow|net.*increase.*decrease.*cash'),
    };
  }

  /**
   * Extract business segments information
   */
  getBusinessSegments(): BusinessSegment[] {
    const segmentSection = this.extractSection('SEGMENT|BUSINESS.*SEGMENT|GEOGRAPHIC.*INFORMATION');
    const segments: BusinessSegment[] = [];

    // Extract segment data using pattern matching
    const segmentPattern = /(\w+(?:\s+\w+)*)\s+segment.*?revenue.*?\$?([\d,]+)/gi;
    let match;
    
    while ((match = segmentPattern.exec(segmentSection)) !== null) {
      segments.push({
        name: match[1].trim(),
        revenue: this.parseNumber(match[2]),
        operatingIncome: 0, // Would need more sophisticated parsing
        assets: 0, // Would need more sophisticated parsing
        description: '',
      });
    }

    return segments;
  }

  /**
   * Extract risk factors
   */
  getRiskFactors(): RiskFactor[] {
    const riskSection = this.extractSection('RISK FACTORS|ITEM 1A');
    const riskFactors: RiskFactor[] = [];

    // Split by common risk factor patterns
    const factors = riskSection.split(/(?=•|·|\d+\.|\n\n)/).filter(f => f.trim().length > 50);
    
    factors.forEach(factor => {
      const severity = this.assessRiskSeverity(factor);
      riskFactors.push({
        category: this.extractRiskCategory(factor),
        description: factor.trim().substring(0, 500),
        severity,
      });
    });

    return riskFactors.slice(0, 10); // Limit to top 10 risk factors
  }

  /**
   * Extract Management Discussion & Analysis sections
   */
  getManagementDiscussion(): MDSection[] {
    const mdaSection = this.extractSection('MANAGEMENT.*DISCUSSION|ITEM 2|MD&A');
    const sections: MDSection[] = [];

    // Split into subsections
    const subsections = mdaSection.split(/(?=OVERVIEW|RESULTS OF OPERATIONS|FINANCIAL CONDITION|LIQUIDITY)/i);
    
    subsections.forEach(section => {
      if (section.trim().length > 100) {
        const title = this.extractSectionTitle(section);
        sections.push({
          title,
          content: section.trim().substring(0, 1000),
          keyMetrics: this.extractKeyMetrics(section),
        });
      }
    });

    return sections;
  }

  /**
   * Extract XBRL facts (simplified version)
   */
  getXBRLFacts(): XBRLFact[] {
    const xbrlFacts: XBRLFact[] = [];
    
    // Extract XBRL data if present
    const xbrlPattern = /<ix:nonFraction[^>]*name="([^"]*)"[^>]*contextRef="([^"]*)"[^>]*decimals="([^"]*)"[^>]*unitRef="([^"]*)"[^>]*>([^<]*)</gi;
    let match;
    
    while ((match = xbrlPattern.exec(this.rawContent)) !== null) {
      xbrlFacts.push({
        name: match[1],
        value: this.parseNumber(match[5]),
        units: match[4],
        contextRef: match[2],
        decimals: parseInt(match[3]) || 0,
        period: this.extractPeriodFromContext(match[2]),
      });
    }

    return xbrlFacts;
  }

  /**
   * Calculate financial metrics
   */
  getFinancialMetrics(): FinancialMetrics {
    const balanceSheet = this.parseBalanceSheet();
    const incomeStatement = this.parseIncomeStatement();
    
    return {
      marketCap: null, // Would need stock price data
      peRatio: null, // Would need stock price data
      debtToEquity: this.calculateDebtToEquity(balanceSheet),
      returnOnEquity: this.calculateROE(incomeStatement, balanceSheet),
      currentRatio: this.calculateCurrentRatio(balanceSheet),
      quickRatio: this.calculateQuickRatio(balanceSheet),
    };
  }

  /**
   * Parse complete financial form
   */
  parseAll(): ParsedFinancialForm {
    const header = this.parseHeader();
    const financialStatements = this.getFinancialStatements();
    
    return {
      formType: header.formType,
      filingDate: header.filingDate,
      periodEndDate: header.periodEndDate,
      cik: header.cik,
      companyName: header.companyName,
      ticker: header.ticker,
      balanceSheet: financialStatements.balanceSheet,
      incomeStatement: financialStatements.incomeStatement,
      cashFlowStatement: financialStatements.cashFlowStatement,
      businessSegments: this.getBusinessSegments(),
      riskFactors: this.getRiskFactors(),
      managementDiscussion: this.getManagementDiscussion(),
      xbrlFacts: this.getXBRLFacts(),
      financialMetrics: this.getFinancialMetrics(),
    };
  }

  // Helper methods

  private extractSection(pattern: string): string {
    const regex = new RegExp(pattern, 'i');
    const match = this.rawContent.match(regex);
    if (!match) return '';
    
    const startIndex = match.index || 0;
    const endIndex = this.rawContent.indexOf('</DOCUMENT>', startIndex);
    
    return this.rawContent.substring(startIndex, endIndex > 0 ? endIndex : startIndex + 50000);
  }

  private extractBalanceSheetItems(section: string, pattern: string): BalanceSheetItem[] {
    const items: BalanceSheetItem[] = [];
    const regex = new RegExp(pattern + '.*?\\$([\\d,]+)', 'gi');
    let match;
    
    while ((match = regex.exec(section)) !== null) {
      items.push({
        label: match[0].split('$')[0].trim(),
        value: this.parseNumber(match[1]),
        units: 'USD',
        period: this.extractPeriod(section),
        filed: this.extractFilingDate(),
      });
    }
    
    return items;
  }

  private extractBalanceSheetItem(section: string, pattern: string): BalanceSheetItem | null {
    const items = this.extractBalanceSheetItems(section, pattern);
    return items.length > 0 ? items[0] : null;
  }

  private extractIncomeStatementItems(section: string, pattern: string): IncomeStatementItem[] {
    const items: IncomeStatementItem[] = [];
    const regex = new RegExp(pattern + '.*?\\$([\\d,]+)', 'gi');
    let match;
    
    while ((match = regex.exec(section)) !== null) {
      items.push({
        label: match[0].split('$')[0].trim(),
        value: this.parseNumber(match[1]),
        units: 'USD',
        period: this.extractPeriod(section),
        filed: this.extractFilingDate(),
      });
    }
    
    return items;
  }

  private extractIncomeStatementItem(section: string, pattern: string): IncomeStatementItem | null {
    const items = this.extractIncomeStatementItems(section, pattern);
    return items.length > 0 ? items[0] : null;
  }

  private extractCashFlowItems(section: string, pattern: string): CashFlowItem[] {
    const items: CashFlowItem[] = [];
    const regex = new RegExp(pattern + '.*?\\$([\\d,]+)', 'gi');
    let match;
    
    while ((match = regex.exec(section)) !== null) {
      items.push({
        label: match[0].split('$')[0].trim(),
        value: this.parseNumber(match[1]),
        units: 'USD',
        period: this.extractPeriod(section),
        filed: this.extractFilingDate(),
      });
    }
    
    return items;
  }

  private extractCashFlowItem(section: string, pattern: string): CashFlowItem | null {
    const items = this.extractCashFlowItems(section, pattern);
    return items.length > 0 ? items[0] : null;
  }

  private parseHeader() {
    const cikMatch = this.rawContent.match(/CENTRAL INDEX KEY:\s*(\d+)/);
    const companyMatch = this.rawContent.match(/COMPANY CONFORMED NAME:\s*([^\n\r]+)/);
    const formTypeMatch = this.rawContent.match(/FORM TYPE:\s*([^\n\r]+)/);
    const filingDateMatch = this.rawContent.match(/FILED AS OF DATE:\s*(\d{8})/);
    const periodMatch = this.rawContent.match(/CONFORMED PERIOD OF REPORT:\s*(\d{8})/);
    
    return {
      cik: cikMatch?.[1] || '',
      companyName: companyMatch?.[1]?.trim() || '',
      formType: formTypeMatch?.[1]?.trim() || '',
      ticker: '', // Would need to extract from trading symbol
      filingDate: this.parseDate(filingDateMatch?.[1]),
      periodEndDate: this.parseDate(periodMatch?.[1]),
    };
  }

  private parseNumber(value: string | undefined): number {
    if (!value) return 0;
    return parseFloat(value.replace(/[,$]/g, '')) || 0;
  }

  private parseDate(dateStr?: string): Date {
    if (!dateStr) return new Date();
    
    // Parse YYYYMMDD format
    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1;
    const day = parseInt(dateStr.substring(6, 8));
    
    return new Date(year, month, day);
  }

  private extractPeriod(section: string): string {
    const periodMatch = section.match(/(\d{4})/);
    return periodMatch?.[1] || new Date().getFullYear().toString();
  }

  private extractFilingDate(): Date {
    const dateMatch = this.rawContent.match(/FILED AS OF DATE:\s*(\d{8})/);
    return this.parseDate(dateMatch?.[1]);
  }

  private assessRiskSeverity(riskText: string): 'low' | 'medium' | 'high' {
    const highRiskKeywords = ['material adverse', 'significant risk', 'substantial risk', 'could result in'];
    const mediumRiskKeywords = ['may affect', 'potential impact', 'could impact'];
    
    const text = riskText.toLowerCase();
    
    if (highRiskKeywords.some(keyword => text.includes(keyword))) {
      return 'high';
    } else if (mediumRiskKeywords.some(keyword => text.includes(keyword))) {
      return 'medium';
    }
    
    return 'low';
  }

  private extractRiskCategory(riskText: string): string {
    const categories = [
      { keywords: ['market', 'competition', 'customer'], category: 'Market Risk' },
      { keywords: ['regulation', 'compliance', 'legal'], category: 'Regulatory Risk' },
      { keywords: ['technology', 'cyber', 'security'], category: 'Technology Risk' },
      { keywords: ['financial', 'credit', 'liquidity'], category: 'Financial Risk' },
      { keywords: ['operational', 'supply chain', 'manufacturing'], category: 'Operational Risk' },
    ];
    
    const text = riskText.toLowerCase();
    
    for (const cat of categories) {
      if (cat.keywords.some(keyword => text.includes(keyword))) {
        return cat.category;
      }
    }
    
    return 'General Risk';
  }

  private extractSectionTitle(section: string): string {
    const lines = section.split('\n');
    for (const line of lines.slice(0, 5)) {
      if (line.trim().length > 10 && line.trim().length < 100) {
        return line.trim();
      }
    }
    return 'Management Discussion';
  }

  private extractKeyMetrics(section: string): Array<{ metric: string; value: string; change: string }> {
    const metrics: Array<{ metric: string; value: string; change: string }> = [];
    
    // Extract percentage changes
    const changePattern = /(\w+(?:\s+\w+)*)\s+(?:increased|decreased|changed)\s+by\s+([\d.]+%)/gi;
    let match;
    
    while ((match = changePattern.exec(section)) !== null) {
      metrics.push({
        metric: match[1].trim(),
        value: '',
        change: match[2],
      });
    }
    
    return metrics.slice(0, 5);
  }

  private extractPeriodFromContext(contextRef: string): string {
    const periodMatch = contextRef.match(/(\d{4})/);
    return periodMatch?.[1] || new Date().getFullYear().toString();
  }

  private calculateDebtToEquity(balanceSheet: BalanceSheet): number | null {
    const totalLiabilities = balanceSheet.liabilities.totalLiabilities?.value;
    const totalEquity = balanceSheet.equity.totalEquity?.value;
    
    if (totalLiabilities && totalEquity && totalEquity !== 0) {
      return totalLiabilities / totalEquity;
    }
    
    return null;
  }

  private calculateROE(incomeStatement: IncomeStatement, balanceSheet: BalanceSheet): number | null {
    const netIncome = incomeStatement.netIncome?.value;
    const totalEquity = balanceSheet.equity.totalEquity?.value;
    
    if (netIncome && totalEquity && totalEquity !== 0) {
      return netIncome / totalEquity;
    }
    
    return null;
  }

  private calculateCurrentRatio(balanceSheet: BalanceSheet): number | null {
    const currentAssets = balanceSheet.assets.currentAssets.reduce((sum, asset) => sum + asset.value, 0);
    const currentLiabilities = balanceSheet.liabilities.currentLiabilities.reduce((sum, liability) => sum + liability.value, 0);
    
    if (currentAssets && currentLiabilities && currentLiabilities !== 0) {
      return currentAssets / currentLiabilities;
    }
    
    return null;
  }

  private calculateQuickRatio(balanceSheet: BalanceSheet): number | null {
    // Calculate quick assets (current assets minus inventory and prepaid expenses)
    const currentAssets = balanceSheet.assets.currentAssets;
    let quickAssets = 0;
    
    for (const asset of currentAssets) {
      // Exclude inventory and prepaid expenses from quick assets
      const label = asset.label.toLowerCase();
      if (!label.includes('inventory') && 
          !label.includes('prepaid') && 
          !label.includes('deferred') &&
          !label.includes('other current assets')) {
        quickAssets += asset.value;
      }
    }
    
    // If no specific quick assets found, use a conservative estimate
    if (quickAssets === 0 && currentAssets.length > 0) {
      const totalCurrentAssets = currentAssets.reduce((sum, asset) => sum + asset.value, 0);
      // Find inventory value if available
      const inventory = currentAssets.find(asset => 
        asset.label.toLowerCase().includes('inventory')
      );
      
      if (inventory) {
        quickAssets = totalCurrentAssets - inventory.value;
      } else {
        // Conservative estimate: assume 20% of current assets are inventory/prepaid
        quickAssets = totalCurrentAssets * 0.8;
      }
    }
    
    const currentLiabilities = balanceSheet.liabilities.currentLiabilities.reduce(
      (sum, liability) => sum + liability.value, 0
    );
    
    if (quickAssets && currentLiabilities && currentLiabilities !== 0) {
      return quickAssets / currentLiabilities;
    }
    
    return null;
  }
}