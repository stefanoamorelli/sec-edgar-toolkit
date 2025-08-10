/**
 * Tests for comprehensive error handling
 */

import {
  SecEdgarApiError,
  RateLimitError,
  InvalidUserAgentError,
  CompanyNotFoundError,
  InvalidFormTypeError,
  TimeoutError,
  NetworkError,
  RequestError,
  FilingNotFoundError,
  XMLParsingError,
  ConceptNotFoundError,
  ErrorHandler,
  ErrorWithContext
} from '../exceptions';

describe('Error Classes', () => {
  describe('InvalidUserAgentError', () => {
    it('should create error for missing user agent', () => {
      const error = new InvalidUserAgentError();
      expect(error.message).toContain('User agent is required');
      expect(error.field).toBe('userAgent');
      expect(error.name).toBe('InvalidUserAgentError');
    });

    it('should create error for invalid user agent', () => {
      const error = new InvalidUserAgentError('Bot');
      expect(error.message).toContain('Invalid user agent format');
      expect(error.message).toContain('Bot');
    });
  });

  describe('CompanyNotFoundError', () => {
    it('should include identifier and search type', () => {
      const error = new CompanyNotFoundError('AAPL', 'ticker');
      expect(error.message).toBe('Company not found: AAPL (searched by ticker)');
      expect(error.identifier).toBe('AAPL');
      expect(error.searchType).toBe('ticker');
      expect(error.statusCode).toBe(404);
    });

    it('should handle CIK search', () => {
      const error = new CompanyNotFoundError('0000320193', 'cik');
      expect(error.message).toContain('0000320193');
      expect(error.searchType).toBe('cik');
    });
  });

  describe('InvalidFormTypeError', () => {
    it('should show invalid form type', () => {
      const error = new InvalidFormTypeError('INVALID-FORM');
      expect(error.message).toBe('Invalid form type: "INVALID-FORM"');
    });

    it('should include valid types when provided', () => {
      const validTypes = ['10-K', '10-Q', '8-K'];
      const error = new InvalidFormTypeError('INVALID', validTypes);
      expect(error.message).toContain('Valid types: 10-K, 10-Q, 8-K');
    });
  });

  describe('Network Errors', () => {
    it('should create TimeoutError', () => {
      const error = new TimeoutError('https://api.example.com', 30000);
      expect(error.message).toBe('Request timed out after 30000ms');
      expect(error.url).toBe('https://api.example.com');
      expect(error.name).toBe('TimeoutError');
    });

    it('should create NetworkError', () => {
      const originalError = new Error('ECONNREFUSED');
      const error = new NetworkError(
        'Connection refused',
        'https://api.example.com',
        originalError
      );
      expect(error.message).toBe('Connection refused');
      expect(error.url).toBe('https://api.example.com');
      expect(error.originalError).toBe(originalError);
    });

    it('should create RequestError', () => {
      const error = new RequestError(
        'Bad Request',
        'https://api.example.com',
        400,
        { error: 'Invalid parameters' }
      );
      expect(error.statusCode).toBe(400);
      expect(error.response).toEqual({ error: 'Invalid parameters' });
    });
  });

  describe('Filing Errors', () => {
    it('should create FilingNotFoundError', () => {
      const error = new FilingNotFoundError('0000320193-24-000001', '0000320193');
      expect(error.message).toBe('Filing not found: 0000320193-24-000001 for CIK 0000320193');
      expect(error.accessionNumber).toBe('0000320193-24-000001');
      expect(error.cik).toBe('0000320193');
      expect(error.statusCode).toBe(404);
    });
  });

  describe('Parsing Errors', () => {
    it('should create XMLParsingError with location', () => {
      const error = new XMLParsingError('Invalid character', 10, 25);
      expect(error.message).toBe('XML parsing error at line 10, column 25: Invalid character');
      expect(error.lineNumber).toBe(10);
      expect(error.columnNumber).toBe(25);
    });

    it('should create XMLParsingError without location', () => {
      const error = new XMLParsingError('Invalid XML structure');
      expect(error.message).toBe('XML parsing error: Invalid XML structure');
    });
  });

  describe('XBRL Errors', () => {
    it('should create ConceptNotFoundError', () => {
      const error = new ConceptNotFoundError('CustomConcept', 'custom-taxonomy');
      expect(error.message).toBe('XBRL concept not found: CustomConcept in custom-taxonomy');
      expect(error.concept).toBe('CustomConcept');
      expect(error.taxonomy).toBe('custom-taxonomy');
    });
  });
});

describe('ErrorHandler', () => {
  describe('wrapError', () => {
    it('should wrap error with context', () => {
      const originalError = new Error('Database error');
      const wrapped = ErrorHandler.wrapError(
        originalError,
        {
          operation: 'fetchFilings',
          cik: '0000320193',
          formType: '10-K'
        },
        'Failed to fetch filings'
      );

      expect(wrapped).toBeInstanceOf(ErrorWithContext);
      expect(wrapped.message).toBe('Failed to fetch filings');
      expect(wrapped.originalError).toBe(originalError);
      expect(wrapped.context.operation).toBe('fetchFilings');
      expect(wrapped.context.cik).toBe('0000320193');
    });

    it('should use original message if not provided', () => {
      const originalError = new Error('Original message');
      const wrapped = ErrorHandler.wrapError(originalError, {});
      expect(wrapped.message).toBe('Original message');
    });
  });

  describe('normalize', () => {
    it('should return SecEdgarApiError unchanged', () => {
      const error = new SecEdgarApiError('Test error');
      const normalized = ErrorHandler.normalize(error);
      expect(normalized).toBe(error);
    });

    it('should wrap Error in SecEdgarApiError', () => {
      const error = new Error('Regular error');
      const normalized = ErrorHandler.normalize(error);
      expect(normalized).toBeInstanceOf(SecEdgarApiError);
      expect(normalized.message).toBe('Regular error');
    });

    it('should handle string errors', () => {
      const normalized = ErrorHandler.normalize('String error');
      expect(normalized).toBeInstanceOf(SecEdgarApiError);
      expect(normalized.message).toBe('String error');
    });

    it('should handle unknown errors', () => {
      const normalized = ErrorHandler.normalize({ weird: 'object' });
      expect(normalized).toBeInstanceOf(SecEdgarApiError);
      expect(normalized.message).toBe('An unknown error occurred');
    });
  });

  describe('isRetryable', () => {
    it('should identify rate limit errors as retryable', () => {
      const error = new RateLimitError();
      expect(ErrorHandler.isRetryable(error)).toBe(true);
    });

    it('should identify timeout errors as retryable', () => {
      const error = new TimeoutError('url', 30000);
      expect(ErrorHandler.isRetryable(error)).toBe(true);
    });

    it('should identify network errors as retryable', () => {
      const error = new NetworkError('Network error', 'url');
      expect(ErrorHandler.isRetryable(error)).toBe(true);
    });

    it('should identify 5xx errors as retryable', () => {
      const error = new RequestError('Server error', 'url', 503);
      expect(ErrorHandler.isRetryable(error)).toBe(true);
    });

    it('should identify 408 as retryable', () => {
      const error = new RequestError('Request timeout', 'url', 408);
      expect(ErrorHandler.isRetryable(error)).toBe(true);
    });

    it('should not retry 4xx errors', () => {
      const error = new RequestError('Bad request', 'url', 400);
      expect(ErrorHandler.isRetryable(error)).toBe(false);
    });

    it('should not retry non-network errors', () => {
      const error = new InvalidFormTypeError('10-X');
      expect(ErrorHandler.isRetryable(error)).toBe(false);
    });
  });

  describe('getRetryDelay', () => {
    it('should use longer delay for rate limits', () => {
      const error = new RateLimitError();
      expect(ErrorHandler.getRetryDelay(error, 1)).toBe(10000);  // 2^1 * 5000
      expect(ErrorHandler.getRetryDelay(error, 2)).toBe(20000);  // 2^2 * 5000
      expect(ErrorHandler.getRetryDelay(error, 3)).toBe(40000);  // 2^3 * 5000
    });

    it('should cap rate limit delay at 60 seconds', () => {
      const error = new RateLimitError();
      expect(ErrorHandler.getRetryDelay(error, 10)).toBe(60000);
    });

    it('should use exponential backoff for other errors', () => {
      const error = new TimeoutError('url', 30000);
      expect(ErrorHandler.getRetryDelay(error, 1)).toBe(2000);
      expect(ErrorHandler.getRetryDelay(error, 2)).toBe(4000);
      expect(ErrorHandler.getRetryDelay(error, 3)).toBe(8000);
    });

    it('should cap other delays at 30 seconds', () => {
      const error = new NetworkError('error', 'url');
      expect(ErrorHandler.getRetryDelay(error, 10)).toBe(30000);
    });
  });
});

describe('ErrorWithContext', () => {
  it('should format toString with context', () => {
    const error = new ErrorWithContext(
      'Test error',
      {
        operation: 'test',
        url: 'https://example.com',
        attempt: 3
      }
    );

    const str = error.toString();
    expect(str).toContain('ErrorWithContext');
    expect(str).toContain('Test error');
    expect(str).toContain('operation=test');
    expect(str).toContain('url=https://example.com');
    expect(str).toContain('attempt=3');
  });
});