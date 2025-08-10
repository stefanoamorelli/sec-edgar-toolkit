/**
 * Tests for financial forms parser
 */

import { readFileSync } from 'fs';
import { join } from 'path';
import { FinancialFormParser } from '../parsers/financial-forms';

describe('FinancialFormParser', () => {
  let parser: FinancialFormParser;
  let apple10K: string;

  beforeAll(() => {
    const fixturePath = join(__dirname, '../../tests/fixtures/forms/10-K/apple_10k_2023.txt');
    apple10K = readFileSync(fixturePath, 'utf-8');
    parser = new FinancialFormParser(apple10K);
  });

  describe('parseAll', () => {
    it('should parse basic document information', () => {
      const result = parser.parseAll();
      
      expect(result.formType).toBe('10-K');
      expect(result.cik).toBe('0000320193');
      expect(result.companyName).toBe('Apple Inc.');
      expect(result.filingDate).toBeInstanceOf(Date);
      expect(result.periodEndDate).toBeInstanceOf(Date);
    });

    it('should extract financial statements structure', () => {
      const result = parser.parseAll();
      
      expect(result.balanceSheet).toBeDefined();
      expect(result.balanceSheet.assets).toBeDefined();
      expect(result.balanceSheet.liabilities).toBeDefined();
      expect(result.balanceSheet.equity).toBeDefined();
      
      expect(result.incomeStatement).toBeDefined();
      expect(result.cashFlowStatement).toBeDefined();
    });

    it('should extract business segments', () => {
      const segments = parser.getBusinessSegments();
      
      expect(Array.isArray(segments)).toBe(true);
      // Apple typically has product and geographic segments
    });

    it('should extract risk factors', () => {
      const riskFactors = parser.getRiskFactors();
      
      expect(Array.isArray(riskFactors)).toBe(true);
      expect(riskFactors.length).toBeGreaterThan(0);
      
      if (riskFactors.length > 0) {
        expect(riskFactors[0]).toHaveProperty('category');
        expect(riskFactors[0]).toHaveProperty('description');
        expect(riskFactors[0]).toHaveProperty('severity');
        expect(['low', 'medium', 'high']).toContain(riskFactors[0].severity);
      }
    });

    it('should extract management discussion', () => {
      const mdSections = parser.getManagementDiscussion();
      
      expect(Array.isArray(mdSections)).toBe(true);
      
      if (mdSections.length > 0) {
        expect(mdSections[0]).toHaveProperty('title');
        expect(mdSections[0]).toHaveProperty('content');
        expect(mdSections[0]).toHaveProperty('keyMetrics');
      }
    });

    it('should calculate financial metrics', () => {
      const metrics = parser.getFinancialMetrics();
      
      expect(metrics).toBeDefined();
      expect(typeof metrics.debtToEquity === 'number' || metrics.debtToEquity === null).toBe(true);
      expect(typeof metrics.returnOnEquity === 'number' || metrics.returnOnEquity === null).toBe(true);
      expect(typeof metrics.currentRatio === 'number' || metrics.currentRatio === null).toBe(true);
    });
  });

  describe('getFinancialStatements', () => {
    it('should return structured financial data', () => {
      const statements = parser.getFinancialStatements();
      
      expect(statements).toHaveProperty('balanceSheet');
      expect(statements).toHaveProperty('incomeStatement');
      expect(statements).toHaveProperty('cashFlowStatement');
      
      expect(statements.balanceSheet.assets).toHaveProperty('currentAssets');
      expect(statements.balanceSheet.assets).toHaveProperty('nonCurrentAssets');
      expect(statements.balanceSheet.liabilities).toHaveProperty('currentLiabilities');
      
      expect(Array.isArray(statements.balanceSheet.assets.currentAssets)).toBe(true);
      expect(Array.isArray(statements.incomeStatement.operatingExpenses)).toBe(true);
    });
  });
});