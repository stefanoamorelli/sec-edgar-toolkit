/**
 * HTTP client for SEC EDGAR API with rate limiting and retry logic
 */

import fetch, { Response } from 'node-fetch';
import { SecEdgarApiError, RateLimitError, AuthenticationError, NotFoundError } from '../exceptions';
import { RequestError, TimeoutError, NetworkError } from '../exceptions/errors';
import { RequestCache, CacheOptions } from './cache';

export interface HttpClientOptions {
  rateLimitDelay?: number;
  maxRetries?: number;
  timeout?: number;
  cache?: CacheOptions | false;
}

export class HttpClient {
  private userAgent: string;
  private rateLimitDelay: number;
  private maxRetries: number;
  private timeout: number;
  private lastRequestTime: number = 0;
  private cache?: RequestCache;

  constructor(
    userAgent: string,
    options: HttpClientOptions = {}
  ) {
    this.userAgent = userAgent;
    this.rateLimitDelay = (options.rateLimitDelay || 0.1) * 1000; // Convert to milliseconds
    this.maxRetries = options.maxRetries || 3;
    this.timeout = options.timeout || 30000;
    
    // Initialize cache if not explicitly disabled
    if (options.cache !== false) {
      const cacheOptions = options.cache || {
        ttl: 300000, // 5 minutes default
        maxSize: 500,
      };
      this.cache = new RequestCache(cacheOptions);
    }
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async enforceRateLimit(): Promise<void> {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    if (timeSinceLastRequest < this.rateLimitDelay) {
      const sleepTime = this.rateLimitDelay - timeSinceLastRequest;
      await this.sleep(sleepTime);
    }
    
    this.lastRequestTime = Date.now();
  }

  private handleHttpError(response: Response, url: string): never {
    const { status, statusText } = response;
    
    switch (status) {
      case 401:
        throw new AuthenticationError(`Authentication failed: ${statusText}`);
      case 404:
        throw new NotFoundError(`Resource not found: ${statusText}`);
      case 429:
        throw new RateLimitError(`Rate limit exceeded: ${statusText}`);
      default:
        throw new RequestError(`HTTP ${status}: ${statusText}`, url, status);
    }
  }

  async get(url: string, options?: { skipCache?: boolean }): Promise<any> {
    // Check cache first unless explicitly skipped
    if (this.cache && !options?.skipCache) {
      const cached = await this.cache.get(url);
      if (cached !== null) {
        return cached;
      }
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        await this.enforceRateLimit();

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'User-Agent': this.userAgent,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
          },
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          this.handleHttpError(response, url);
        }

        const data = await response.json();
        
        // Cache successful responses
        if (this.cache) {
          await this.cache.set(url, data);
        }
        
        return data;

      } catch (error) {
        // Handle timeout errors
        if (error instanceof Error && error.name === 'AbortError') {
          lastError = new TimeoutError(url, this.timeout);
        } 
        // Handle network errors
        else if (error instanceof Error && (error.message.includes('ENOTFOUND') || 
                                           error.message.includes('ECONNREFUSED') ||
                                           error.message.includes('ETIMEDOUT') ||
                                           error.message.includes('NetworkError'))) {
          lastError = new NetworkError(error.message, url, error);
        } 
        // Keep existing SecEdgarApiError
        else if (error instanceof SecEdgarApiError) {
          lastError = error;
          // Don't retry on client errors (4xx) except rate limits
          if (error.statusCode && 
              error.statusCode >= 400 && 
              error.statusCode < 500 && 
              error.statusCode !== 429) {
            throw error;
          }
        }
        else {
          lastError = error as Error;
        }

        // If this is the last attempt, throw the error
        if (attempt === this.maxRetries) {
          break;
        }

        // Exponential backoff for retries
        const backoffTime = Math.pow(2, attempt) * 1000;
        await this.sleep(backoffTime);
      }
    }

    throw lastError || new SecEdgarApiError('Max retries exceeded');
  }

  /**
   * Clear the cache
   */
  async clearCache(): Promise<void> {
    if (this.cache) {
      await this.cache.invalidateUrl('');
    }
  }

  /**
   * Invalidate cache entries for a specific URL pattern
   */
  async invalidateCache(urlPattern: string): Promise<void> {
    if (this.cache) {
      await this.cache.invalidateUrl(urlPattern);
    }
  }
}