/**
 * Comprehensive error classes for SEC EDGAR Toolkit
 * 
 * This module provides a rich hierarchy of error classes for better
 * error handling and debugging throughout the TypeScript SDK.
 */

import { SecEdgarApiError, RateLimitError } from './base';

/**
 * Configuration errors
 */
export class ConfigurationError extends SecEdgarApiError {
  constructor(message: string, public field?: string) {
    super(message);
    this.name = 'ConfigurationError';
  }
}

export class InvalidUserAgentError extends ConfigurationError {
  constructor(userAgent?: string) {
    const message = userAgent
      ? `Invalid user agent format: "${userAgent}". Must include contact information.`
      : 'User agent is required and must include contact information.';
    super(message, 'userAgent');
    this.name = 'InvalidUserAgentError';
  }
}

/**
 * API request errors
 */
export class RequestError extends SecEdgarApiError {
  constructor(
    message: string,
    public url?: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message, statusCode);
    this.name = 'RequestError';
  }
}

export class TimeoutError extends RequestError {
  constructor(url: string, timeout: number) {
    super(`Request timed out after ${timeout}ms`, url);
    this.name = 'TimeoutError';
  }
}

export class NetworkError extends RequestError {
  constructor(message: string, url?: string, public originalError?: Error) {
    super(message, url);
    this.name = 'NetworkError';
  }
}

/**
 * Data validation errors
 */
export class ValidationError extends SecEdgarApiError {
  constructor(message: string, public field?: string, public value?: any) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class InvalidCIKError extends ValidationError {
  constructor(cik: string | number) {
    super(
      `Invalid CIK format: "${cik}". CIK must be a number or numeric string.`,
      'cik',
      cik
    );
    this.name = 'InvalidCIKError';
  }
}

export class InvalidDateError extends ValidationError {
  constructor(date: string, expectedFormat: string = 'YYYY-MM-DD') {
    super(
      `Invalid date format: "${date}". Expected format: ${expectedFormat}`,
      'date',
      date
    );
    this.name = 'InvalidDateError';
  }
}

export class InvalidFormTypeError extends ValidationError {
  constructor(formType: string, validTypes?: string[]) {
    const message = validTypes
      ? `Invalid form type: "${formType}". Valid types: ${validTypes.join(', ')}`
      : `Invalid form type: "${formType}"`;
    super(message, 'formType', formType);
    this.name = 'InvalidFormTypeError';
  }
}

/**
 * Company lookup errors
 */
export class CompanyNotFoundError extends SecEdgarApiError {
  constructor(public identifier: string | number, public searchType: 'ticker' | 'cik' | 'name') {
    const message = `Company not found: ${identifier} (searched by ${searchType})`;
    super(message, 404);
    this.name = 'CompanyNotFoundError';
  }
}

export class MultipleCompaniesFoundError extends SecEdgarApiError {
  constructor(public identifier: string, public count: number) {
    super(`Multiple companies found for "${identifier}": ${count} matches`);
    this.name = 'MultipleCompaniesFoundError';
  }
}

/**
 * Filing errors
 */
export class FilingNotFoundError extends SecEdgarApiError {
  constructor(
    public accessionNumber: string,
    public cik?: string
  ) {
    const message = cik
      ? `Filing not found: ${accessionNumber} for CIK ${cik}`
      : `Filing not found: ${accessionNumber}`;
    super(message, 404);
    this.name = 'FilingNotFoundError';
  }
}

export class FilingContentError extends SecEdgarApiError {
  constructor(
    message: string,
    public accessionNumber: string,
    public contentType?: string
  ) {
    super(message);
    this.name = 'FilingContentError';
  }
}

/**
 * Parsing errors
 */
export class ParsingError extends SecEdgarApiError {
  constructor(
    message: string,
    public documentType?: string,
    public section?: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'ParsingError';
  }
}

export class XMLParsingError extends ParsingError {
  constructor(message: string, public lineNumber?: number, public columnNumber?: number) {
    const location = lineNumber && columnNumber 
      ? ` at line ${lineNumber}, column ${columnNumber}`
      : '';
    super(`XML parsing error${location}: ${message}`, 'XML');
    this.name = 'XMLParsingError';
  }
}

export class JSONParsingError extends ParsingError {
  constructor(message: string, public json?: string) {
    super(`JSON parsing error: ${message}`, 'JSON');
    this.name = 'JSONParsingError';
  }
}

/**
 * XBRL-specific errors
 */
export class XBRLError extends SecEdgarApiError {
  constructor(message: string, public concept?: string, public taxonomy?: string) {
    super(message);
    this.name = 'XBRLError';
  }
}

export class ConceptNotFoundError extends XBRLError {
  constructor(concept: string, taxonomy: string = 'us-gaap') {
    super(`XBRL concept not found: ${concept} in ${taxonomy}`, concept, taxonomy);
    this.name = 'ConceptNotFoundError';
  }
}

export class InvalidUnitError extends XBRLError {
  constructor(unit: string, validUnits?: string[]) {
    const message = validUnits
      ? `Invalid XBRL unit: "${unit}". Valid units: ${validUnits.join(', ')}`
      : `Invalid XBRL unit: "${unit}"`;
    super(message);
    this.name = 'InvalidUnitError';
  }
}

/**
 * Cache errors
 */
export class CacheError extends SecEdgarApiError {
  constructor(message: string, public operation?: string) {
    super(message);
    this.name = 'CacheError';
  }
}

/**
 * Error utilities
 */
export interface ErrorContext {
  operation?: string;
  url?: string;
  cik?: string;
  ticker?: string;
  formType?: string;
  accessionNumber?: string;
  [key: string]: any;
}

export class ErrorWithContext extends SecEdgarApiError {
  constructor(
    message: string,
    public context: ErrorContext,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'ErrorWithContext';
  }

  toString(): string {
    const contextStr = Object.entries(this.context)
      .map(([key, value]) => `${key}=${value}`)
      .join(', ');
    return `${this.name}: ${this.message} [${contextStr}]`;
  }
}

/**
 * Error handler utility
 */
export class ErrorHandler {
  /**
   * Wrap an error with additional context
   */
  static wrapError(
    error: Error,
    context: ErrorContext,
    message?: string
  ): ErrorWithContext {
    const finalMessage = message || error.message;
    return new ErrorWithContext(finalMessage, context, error);
  }

  /**
   * Convert unknown errors to SecEdgarApiError
   */
  static normalize(error: unknown): SecEdgarApiError {
    if (error instanceof SecEdgarApiError) {
      return error;
    }

    if (error instanceof Error) {
      return new SecEdgarApiError(error.message);
    }

    if (typeof error === 'string') {
      return new SecEdgarApiError(error);
    }

    return new SecEdgarApiError('An unknown error occurred');
  }

  /**
   * Check if error is retryable
   */
  static isRetryable(error: Error): boolean {
    if (error instanceof RateLimitError) return true;
    if (error instanceof TimeoutError) return true;
    if (error instanceof NetworkError) return true;
    
    if (error instanceof RequestError) {
      // Retry on 5xx errors (server errors)
      if (error.statusCode && error.statusCode >= 500) return true;
      // Retry on 408 (Request Timeout)
      if (error.statusCode === 408) return true;
    }

    return false;
  }

  /**
   * Get retry delay for an error
   */
  static getRetryDelay(error: Error, attempt: number): number {
    if (error instanceof RateLimitError) {
      // Use longer delay for rate limits
      return Math.min(60000, Math.pow(2, attempt) * 5000);
    }

    // Exponential backoff for other errors
    return Math.min(30000, Math.pow(2, attempt) * 1000);
  }
}

// Re-export base errors
export { SecEdgarApiError, AuthenticationError, NotFoundError } from './base';