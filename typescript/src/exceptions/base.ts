/**
 * Base exception classes for SEC EDGAR Toolkit
 */

export class SecEdgarApiError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = 'SecEdgarApiError';
  }
}

export class RateLimitError extends SecEdgarApiError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 429);
    this.name = 'RateLimitError';
  }
}

export class AuthenticationError extends SecEdgarApiError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends SecEdgarApiError {
  constructor(message: string = 'Resource not found') {
    super(message, 404);
    this.name = 'NotFoundError';
  }
}