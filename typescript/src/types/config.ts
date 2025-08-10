/**
 * Configuration type definitions
 */

export interface EdgarClientConfig {
  userAgent?: string;
  rateLimitDelay?: number;
  maxRetries?: number;
  timeout?: number;
  cache?: false | {
    ttl?: number;
    maxSize?: number;
  };
}

export interface RequestOptions {
  submissionType?: string;
  fromDate?: string;
  toDate?: string;
  unit?: string;
  quarter?: number;
  instantaneous?: boolean;
}