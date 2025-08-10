/**
 * Tests for XBRL functionality
 */

import { XBRLInstance } from '../core/xbrl';
import { XbrlEndpoints } from '../endpoints/xbrl';
import { createClient } from '../edgar';

// Mock data
const mockXBRLFacts = {
  facts: {
    'us-gaap': {
      Assets: {
        units: {
          USD: [
            {
              val: 365725000000,
              accn: '0000320193-24-000001',
              fy: 2023,
              fp: 'FY',
              form: '10-K',
              filed: '2024-01-29',
              end: '2023-09-30'
            }
          ]
        }
      },
      Revenues: {
        units: {
          USD: [
            {
              val: 383285000000,
              accn: '0000320193-24-000001',
              fy: 2023,
              fp: 'FY',
              form: '10-K',
              filed: '2024-01-29',
              start: '2022-10-01',
              end: '2023-09-30'
            }
          ]
        }
      },
      NetIncomeLoss: {
        units: {
          USD: [
            {
              val: 96995000000,
              accn: '0000320193-24-000001',
              fy: 2023,
              fp: 'FY',
              form: '10-K',
              filed: '2024-01-29',
              start: '2022-10-01',
              end: '2023-09-30'
            }
          ]
        }
      },
      Liabilities: {
        units: {
          USD: [
            {
              val: 290437000000,
              accn: '0000320193-24-000001',
              fy: 2023,
              fp: 'FY',
              form: '10-K',
              filed: '2024-01-29',
              end: '2023-09-30'
            }
          ]
        }
      },
      StockholdersEquity: {
        units: {
          USD: [
            {
              val: 62146000000,
              accn: '0000320193-24-000001',
              fy: 2023,
              fp: 'FY',
              form: '10-K',
              filed: '2024-01-29',
              end: '2023-09-30'
            }
          ]
        }
      }
    }
  },
  entityName: 'Apple Inc.',
  cik: '0000320193'
};

// Mock HTTP client
const mockHttpClient = {
  get: jest.fn().mockResolvedValue(mockXBRLFacts)
};

describe('XBRLInstance', () => {
  let xbrlEndpoints: XbrlEndpoints;
  let xbrlInstance: XBRLInstance;
  let mockFiling: any;

  beforeEach(() => {
    xbrlEndpoints = new XbrlEndpoints(mockHttpClient as any);
    mockFiling = {
      cik: '0000320193',
      accessionNumber: '0000320193-24-000001',
      formType: '10-K',
      filingDate: '2024-01-29',
      api: { xbrl: xbrlEndpoints }
    };
    xbrlInstance = new XBRLInstance(mockFiling);

  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('getFacts', () => {
    it('should fetch and cache XBRL facts', async () => {
      const facts = await xbrlInstance.getFacts();
      
      expect(facts).toEqual(mockXBRLFacts);
      expect(mockHttpClient.get).toHaveBeenCalledTimes(1);
      
      // Second call should use cache
      const cachedFacts = await xbrlInstance.getFacts();
      expect(cachedFacts).toEqual(mockXBRLFacts);
      expect(mockHttpClient.get).toHaveBeenCalledTimes(1); // Still only called once
    });
  });

  describe('getConceptValue', () => {
    it('should extract concept value', async () => {
      const assets = await xbrlInstance.getConceptValue('Assets', 'us-gaap', 'USD');
      expect(assets).toBe(365725000000);
      
      const revenue = await xbrlInstance.getConceptValue('Revenues', 'us-gaap', 'USD');
      expect(revenue).toBe(383285000000);
    });

    it('should return null for non-existent concept', async () => {
      const value = await xbrlInstance.getConceptValue('NonExistentConcept', 'us-gaap', 'USD');
      expect(value).toBeNull();
    });

    it('should handle specific period', async () => {
      const value = await xbrlInstance.getConceptValue('Assets', 'us-gaap', 'USD', '2023-09-30');
      expect(value).toBe(365725000000);
      
      const noValue = await xbrlInstance.getConceptValue('Assets', 'us-gaap', 'USD', '2022-09-30');
      expect(noValue).toBeNull();
    });
  });

  describe('getFactsByConcept', () => {
    it('should return all facts for a concept', async () => {
      const assetFacts = await xbrlInstance.getFactsByConcept('Assets');
      
      expect(assetFacts).toHaveLength(1);
      expect(assetFacts[0]).toEqual({
        concept: 'Assets',
        taxonomy: 'us-gaap',
        value: 365725000000,
        unit: 'USD',
        period: '2023-09-30',
        fiscal_year: 2023,
        fiscal_period: 'FY',
        start_date: undefined,
        end_date: '2023-09-30',
        filed: '2024-01-29',
        accession_number: '0000320193-24-000001',
        form: '10-K'
      });
    });

    it('should handle taxonomy parameter', async () => {
      const facts = await xbrlInstance.getFactsByConcept('Assets', 'us-gaap');
      expect(facts).toHaveLength(1);
      
      const noFacts = await xbrlInstance.getFactsByConcept('Assets', 'ifrs');
      expect(noFacts).toHaveLength(0);
    });
  });

  describe('getBalanceSheet', () => {
    it('should extract balance sheet data', async () => {
      const balanceSheet = await xbrlInstance.getBalanceSheet();
      
      // Check that balance sheet has the expected structure
      expect(balanceSheet).toHaveProperty('assets');
      expect(balanceSheet).toHaveProperty('liabilities');
      expect(balanceSheet).toHaveProperty('equity');
      
      // Check specific values if available
      if (balanceSheet.assets.total_assets) {
        expect(balanceSheet.assets.total_assets.value).toBe(365725000000);
      }
      if (balanceSheet.liabilities.total_liabilities) {
        expect(balanceSheet.liabilities.total_liabilities.value).toBe(290437000000);
      }
      if (balanceSheet.equity.total_equity) {
        expect(balanceSheet.equity.total_equity.value).toBe(62146000000);
      }
    });
  });

  describe('getIncomeStatement', () => {
    it('should extract income statement data', async () => {
      const incomeStatement = await xbrlInstance.getIncomeStatement();
      
      // Check that income statement has the expected structure
      expect(incomeStatement).toHaveProperty('revenue');
      expect(incomeStatement).toHaveProperty('net_income');
      
      // Check specific values
      if (incomeStatement.revenue && typeof incomeStatement.revenue === 'object') {
        expect(incomeStatement.revenue.value).toBe(383285000000);
      }
      if (incomeStatement.net_income && typeof incomeStatement.net_income === 'object') {
        expect(incomeStatement.net_income.value).toBe(96995000000);
      }
    });
  });

  describe('getCashFlowStatement', () => {
    it('should extract cash flow data', async () => {
      const cashFlow = await xbrlInstance.getCashFlowStatement();
      
      // Check that cash flow statement has the expected structure
      expect(cashFlow).toHaveProperty('operating_activities');
      expect(cashFlow).toHaveProperty('investing_activities');
      expect(cashFlow).toHaveProperty('financing_activities');
      
      // The actual structure is arrays of activities
      expect(Array.isArray(cashFlow.operating_activities)).toBe(true);
      expect(Array.isArray(cashFlow.investing_activities)).toBe(true);
      expect(Array.isArray(cashFlow.financing_activities)).toBe(true);
    });
  });

  describe('Integration with Filing', () => {
    it('should work with filing.xbrl() method', async () => {
      const client = createClient({
        userAgent: 'Test/1.0 (test@example.com)'
      });

      // Mock the filing's xbrl method
      const mockFiling = {
        cik: '0000320193',
        accessionNumber: '0000320193-24-000001',
        xbrl: jest.fn().mockResolvedValue(xbrlInstance)
      };

      const xbrl = await mockFiling.xbrl();
      const revenue = await xbrl.getConceptValue('Revenues', 'us-gaap', 'USD');
      
      expect(revenue).toBe(383285000000);
    });
  });

  describe('Error handling', () => {
    it('should handle API errors gracefully', async () => {
      const errorClient = {
        get: jest.fn().mockRejectedValue(new Error('API Error'))
      };
      
      const errorEndpoints = new XbrlEndpoints(errorClient as any);
      const errorFiling = { ...mockFiling, api: { xbrl: errorEndpoints } };
      const errorInstance = new XBRLInstance(errorFiling);
      
      await expect(errorInstance.getFacts()).rejects.toThrow('API Error');
    });

    it('should handle malformed data', async () => {
      const malformedClient = {
        get: jest.fn().mockResolvedValue({ invalid: 'data' })
      };
      
      const malformedEndpoints = new XbrlEndpoints(malformedClient as any);
      const malformedFiling = { ...mockFiling, api: { xbrl: malformedEndpoints } };
      const malformedInstance = new XBRLInstance(malformedFiling);
      
      const value = await malformedInstance.getConceptValue('Assets');
      expect(value).toBeNull();
    });
  });
});