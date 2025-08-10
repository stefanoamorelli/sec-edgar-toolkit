/**
 * Comprehensive caching system for SEC EDGAR data
 */

import { createHash } from 'crypto';

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiry?: number;
}

export interface CacheOptions {
  ttl?: number; // Time to live in milliseconds
  maxSize?: number; // Maximum number of entries
  persistent?: boolean; // Whether to persist cache to disk
}

export interface CacheStats {
  size: number;
  hits: number;
  misses: number;
  hitRate: number;
}

export class Cache<T = any> {
  private cache: Map<string, CacheEntry<T>> = new Map();
  private options: Required<CacheOptions>;
  private accessOrder: string[] = [];
  private hits: number = 0;
  private misses: number = 0;

  constructor(options: CacheOptions = {}) {
    this.options = {
      ttl: options.ttl || 3600000, // 1 hour default
      maxSize: options.maxSize || 1000,
      persistent: options.persistent || false,
    };
  }

  /**
   * Get an item from cache
   */
  get(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.misses++;
      return null;
    }

    // Check if expired
    if (entry.expiry && Date.now() > entry.expiry) {
      this.cache.delete(key);
      this.removeFromAccessOrder(key);
      this.misses++;
      return null;
    }

    // Update access order for LRU
    this.updateAccessOrder(key);
    this.hits++;
    
    return entry.data;
  }

  /**
   * Set an item in cache
   */
  set(key: string, data: T, ttl?: number): void {
    const expiry = ttl || this.options.ttl;
    
    // Check size limit
    if (this.cache.size >= this.options.maxSize && !this.cache.has(key)) {
      this.evictLRU();
    }

    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expiry: expiry > 0 ? Date.now() + expiry : undefined,
    };

    this.cache.set(key, entry);
    this.updateAccessOrder(key);
  }

  /**
   * Delete an item from cache
   */
  delete(key: string): boolean {
    this.removeFromAccessOrder(key);
    return this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
  }

  /**
   * Check if key exists in cache
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;
    
    // Check expiry
    if (entry.expiry && Date.now() > entry.expiry) {
      this.delete(key);
      return false;
    }
    
    return true;
  }

  /**
   * Get cache size
   */
  get size(): number {
    return this.cache.size;
  }

  /**
   * Get all keys
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return {
      size: this.cache.size,
      hits: this.hits,
      misses: this.misses,
      hitRate: this.hits + this.misses > 0 ? this.hits / (this.hits + this.misses) : 0,
    };
  }

  /**
   * Invalidate entries matching a pattern
   */
  invalidatePattern(pattern: RegExp): number {
    let count = 0;
    
    for (const key of this.cache.keys()) {
      if (pattern.test(key)) {
        this.delete(key);
        count++;
      }
    }
    
    return count;
  }

  /**
   * Clean up expired entries
   */
  cleanup(): number {
    let count = 0;
    const now = Date.now();
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.expiry && now > entry.expiry) {
        this.delete(key);
        count++;
      }
    }
    
    return count;
  }

  /**
   * Generate cache key from multiple values
   */
  static generateKey(...values: any[]): string {
    const hash = createHash('md5');
    hash.update(JSON.stringify(values));
    return hash.digest('hex');
  }

  /**
   * Update access order for LRU eviction
   */
  private updateAccessOrder(key: string): void {
    this.removeFromAccessOrder(key);
    this.accessOrder.push(key);
  }

  /**
   * Remove key from access order
   */
  private removeFromAccessOrder(key: string): void {
    const index = this.accessOrder.indexOf(key);
    if (index > -1) {
      this.accessOrder.splice(index, 1);
    }
  }

  /**
   * Evict least recently used item
   */
  private evictLRU(): void {
    if (this.accessOrder.length > 0) {
      const lruKey = this.accessOrder[0];
      this.delete(lruKey);
    }
  }
}

/**
 * Decorator for caching method results
 */
export function cacheable(options: CacheOptions = {}) {
  const cache = new Cache(options);
  
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    
    descriptor.value = async function (...args: any[]) {
      const cacheKey = Cache.generateKey(propertyKey, ...args);
      
      // Check cache first
      const cached = cache.get(cacheKey);
      if (cached !== null) {
        return cached;
      }
      
      // Call original method
      const result = await originalMethod.apply(this, args);
      
      // Cache result
      cache.set(cacheKey, result);
      
      return result;
    };
    
    return descriptor;
  };
}

/**
 * Multi-level cache supporting memory and persistent storage
 */
export class MultiLevelCache<T = any> {
  private memoryCache: Cache<T>;
  private persistentCache?: Cache<T>; // Would implement with file system or IndexedDB
  
  constructor(options: CacheOptions = {}) {
    this.memoryCache = new Cache(options);
    
    if (options.persistent) {
      // Initialize persistent cache (implementation would depend on environment)
      // For Node.js: use file system
      // For browser: use IndexedDB or localStorage
    }
  }
  
  async get(key: string): Promise<T | null> {
    // Check memory cache first
    let data = this.memoryCache.get(key);
    if (data !== null) {
      return data;
    }
    
    // Check persistent cache
    if (this.persistentCache) {
      data = await this.persistentCache.get(key);
      if (data !== null) {
        // Promote to memory cache
        this.memoryCache.set(key, data);
        return data;
      }
    }
    
    return null;
  }
  
  async set(key: string, data: T, ttl?: number): Promise<void> {
    // Set in memory cache
    this.memoryCache.set(key, data, ttl);
    
    // Set in persistent cache
    if (this.persistentCache) {
      await this.persistentCache.set(key, data, ttl);
    }
  }
  
  async delete(key: string): Promise<boolean> {
    const memoryDeleted = this.memoryCache.delete(key);
    let persistentDeleted = false;
    
    if (this.persistentCache) {
      persistentDeleted = await this.persistentCache.delete(key);
    }
    
    return memoryDeleted || persistentDeleted;
  }
  
  async clear(): Promise<void> {
    this.memoryCache.clear();
    
    if (this.persistentCache) {
      await this.persistentCache.clear();
    }
  }
}

/**
 * Request cache specifically for HTTP responses
 */
export class RequestCache {
  private cache: MultiLevelCache<any>;
  
  constructor(options: CacheOptions = {}) {
    this.cache = new MultiLevelCache(options);
  }
  
  /**
   * Generate cache key for HTTP request
   */
  private generateRequestKey(url: string, options?: any): string {
    return Cache.generateKey(url, options);
  }
  
  /**
   * Get cached response
   */
  async get(url: string, options?: any): Promise<any | null> {
    const key = this.generateRequestKey(url, options);
    return await this.cache.get(key);
  }
  
  /**
   * Cache response
   */
  async set(url: string, response: any, options?: any, ttl?: number): Promise<void> {
    const key = this.generateRequestKey(url, options);
    await this.cache.set(key, response, ttl);
  }
  
  /**
   * Delete cached response
   */
  async delete(url: string, options?: any): Promise<boolean> {
    const key = this.generateRequestKey(url, options);
    return await this.cache.delete(key);
  }
  
  /**
   * Invalidate all cache entries for a base URL
   */
  async invalidateUrl(_baseUrl: string): Promise<void> {
    // This would need to track keys by URL pattern
    // For now, simplified implementation
    await this.cache.clear();
  }
}

// Export singleton instances for common use cases
export const globalCache = new Cache({ ttl: 3600000, maxSize: 1000 });
export const requestCache = new RequestCache({ ttl: 300000, maxSize: 500 });