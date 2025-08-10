/**
 * Tests for EdgarClient
 */

import { EdgarClient } from '../client/edgar-client';

// Mock node-fetch
jest.mock('node-fetch');

describe('EdgarClient', () => {
  let client: EdgarClient;
  
  beforeEach(() => {
    client = new EdgarClient({ 
      userAgent: 'TestApp/1.0 (test@example.com)',
      rateLimitDelay: 0 // Disable rate limiting for tests
    });
  });

  describe('constructor', () => {
    it('should create client with valid user agent', () => {
      expect(client).toBeInstanceOf(EdgarClient);
    });

    it('should throw error with invalid user agent', () => {
      expect(() => {
        new EdgarClient({ userAgent: 'short' });
      }).toThrow('Invalid user agent format');
    });

    it('should throw error when no user agent provided and no env var', () => {
      delete process.env.SEC_EDGAR_TOOLKIT_USER_AGENT;
      expect(() => {
        new EdgarClient();
      }).toThrow('User agent is required');
    });

    it('should use environment variable when no user agent provided', () => {
      process.env.SEC_EDGAR_TOOLKIT_USER_AGENT = 'EnvApp/1.0 (env@example.com)';
      const envClient = new EdgarClient();
      expect(envClient).toBeInstanceOf(EdgarClient);
    });
  });

  describe('getCompanyTickers', () => {
    it('should fetch and cache company tickers', async () => {
      const mockTickers = {
        '0': { cik_str: '0000320193', ticker: 'AAPL', title: 'Apple Inc.' }
      };

      const mockFetch = require('node-fetch') as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTickers,
      } as any);

      const result = await client.getCompanyTickers();
      expect(result).toEqual(mockTickers);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://data.sec.gov/files/company_tickers.json',
        expect.objectContaining({
          headers: expect.objectContaining({
            'User-Agent': 'TestApp/1.0 (test@example.com)'
          })
        })
      );
    });
  });

  describe('getCompanyByTicker', () => {
    beforeEach(() => {
      const mockTickers = {
        '0': { cik_str: '0000320193', ticker: 'AAPL', title: 'Apple Inc.' },
        '1': { cik_str: '0000789019', ticker: 'MSFT', title: 'Microsoft Corporation' }
      };

      jest.spyOn(client.company, 'getCompanyTickers').mockResolvedValue(mockTickers);
    });

    it('should find company by ticker (case insensitive)', async () => {
      const result = await client.getCompanyByTicker('aapl');
      expect(result).toEqual({
        cik_str: '0000320193',
        ticker: 'AAPL',
        title: 'Apple Inc.'
      });
    });

    it('should return null for non-existent ticker', async () => {
      const result = await client.getCompanyByTicker('INVALID');
      expect(result).toBeNull();
    });
  });

  describe('getCompanyByCik', () => {
    beforeEach(() => {
      const mockTickers = {
        '0': { cik_str: '0000320193', ticker: 'AAPL', title: 'Apple Inc.' }
      };

      jest.spyOn(client.company, 'getCompanyTickers').mockResolvedValue(mockTickers);
    });

    it('should find company by CIK string', async () => {
      const result = await client.getCompanyByCik('0000320193');
      expect(result).toEqual({
        cik_str: '0000320193',
        ticker: 'AAPL',
        title: 'Apple Inc.'
      });
    });

    it('should find company by CIK number', async () => {
      const result = await client.getCompanyByCik(320193);
      expect(result).toEqual({
        cik_str: '0000320193',
        ticker: 'AAPL',
        title: 'Apple Inc.'
      });
    });

    it('should return null for non-existent CIK', async () => {
      const result = await client.getCompanyByCik('9999999999');
      expect(result).toBeNull();
    });
  });

  describe('searchCompanies', () => {
    beforeEach(() => {
      const mockTickers = {
        '0': { cik_str: '0000320193', ticker: 'AAPL', title: 'Apple Inc.' },
        '1': { cik_str: '0000789019', ticker: 'MSFT', title: 'Microsoft Corporation' },
        '2': { cik_str: '0001018724', ticker: 'AMZN', title: 'Amazon.com Inc.' }
      };

      jest.spyOn(client.company, 'getCompanyTickers').mockResolvedValue(mockTickers);
    });

    it('should search companies by title', async () => {
      const results = await client.searchCompanies('apple');
      expect(results).toHaveLength(1);
      expect(results[0].ticker).toBe('AAPL');
    });

    it('should search companies by ticker', async () => {
      const results = await client.searchCompanies('msft');
      expect(results).toHaveLength(1);
      expect(results[0].ticker).toBe('MSFT');
    });

    it('should return empty array for no matches', async () => {
      const results = await client.searchCompanies('xyz');
      expect(results).toHaveLength(0);
    });
  });

  describe('getCompanySubmissions', () => {
    it('should fetch company submissions', async () => {
      const mockSubmissions = {
        cik: '0000320193',
        name: 'Apple Inc.',
        filings: { recent: { form: ['10-K'], accessionNumber: ['123'] } }
      };

      const mockFetch = require('node-fetch') as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSubmissions,
      } as any);

      const result = await client.getCompanySubmissions('320193');
      expect(result).toEqual(mockSubmissions);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://data.sec.gov/submissions/CIK0000320193.json',
        expect.any(Object)
      );
    });
  });

  describe('getCompanyFacts', () => {
    it('should fetch company XBRL facts', async () => {
      const mockFacts = {
        cik: '0000320193',
        entityName: 'Apple Inc.',
        facts: {}
      };

      const mockFetch = require('node-fetch') as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockFacts,
      } as any);

      const result = await client.getCompanyFacts('320193');
      expect(result).toEqual(mockFacts);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json',
        expect.any(Object)
      );
    });
  });
});