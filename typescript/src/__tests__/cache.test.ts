/**
 * Tests for caching system
 */

import { Cache, RequestCache } from '../utils/cache';

describe('Cache', () => {
  let cache: Cache<string>;

  beforeEach(() => {
    cache = new Cache<string>({
      ttl: 1000, // 1 second TTL for testing
      maxSize: 3
    });
  });

  describe('basic operations', () => {
    it('should set and get values', async () => {
      await cache.set('key1', 'value1');
      const value = await cache.get('key1');
      expect(value).toBe('value1');
    });

    it('should return null for non-existent keys', async () => {
      const value = await cache.get('nonexistent');
      expect(value).toBeNull();
    });

    it('should check if key exists', async () => {
      await cache.set('key1', 'value1');
      expect(await cache.has('key1')).toBe(true);
      expect(await cache.has('nonexistent')).toBe(false);
    });

    it('should delete values', async () => {
      await cache.set('key1', 'value1');
      expect(await cache.has('key1')).toBe(true);
      
      await cache.delete('key1');
      expect(await cache.has('key1')).toBe(false);
    });

    it('should clear all values', async () => {
      await cache.set('key1', 'value1');
      await cache.set('key2', 'value2');
      expect(cache.getStats().size).toBe(2);
      
      await cache.clear();
      expect(cache.getStats().size).toBe(0);
    });
  });

  describe('TTL expiration', () => {
    it('should expire entries after TTL', async () => {
      await cache.set('key1', 'value1');
      expect(await cache.get('key1')).toBe('value1');
      
      // Wait for TTL to expire
      await new Promise(resolve => setTimeout(resolve, 1100));
      
      expect(await cache.get('key1')).toBeNull();
    });

    it('should update expiry on set', async () => {
      await cache.set('key1', 'value1');
      
      // Wait half the TTL
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Update the value (should reset TTL)
      await cache.set('key1', 'updated');
      
      // Wait another half TTL (original would have expired)
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // Should still be available
      expect(await cache.get('key1')).toBe('updated');
    });
  });

  describe('LRU eviction', () => {
    it('should evict least recently used when full', async () => {
      // Fill cache to capacity
      await cache.set('key1', 'value1');
      await cache.set('key2', 'value2');
      await cache.set('key3', 'value3');
      
      // Access key1 and key2 to make them recently used
      await cache.get('key1');
      await cache.get('key2');
      
      // Add new item - should evict key3 (least recently used)
      await cache.set('key4', 'value4');
      
      expect(await cache.has('key1')).toBe(true);
      expect(await cache.has('key2')).toBe(true);
      expect(await cache.has('key3')).toBe(false); // Evicted
      expect(await cache.has('key4')).toBe(true);
    });

    it('should update access order on get', async () => {
      await cache.set('key1', 'value1');
      await cache.set('key2', 'value2');
      await cache.set('key3', 'value3');
      
      // Access key1 to make it most recently used
      await cache.get('key1');
      
      // Add new item - should evict key2 (now least recently used)
      await cache.set('key4', 'value4');
      
      expect(await cache.has('key1')).toBe(true);
      expect(await cache.has('key2')).toBe(false); // Evicted
      expect(await cache.has('key3')).toBe(true);
      expect(await cache.has('key4')).toBe(true);
    });
  });

  describe('statistics', () => {
    it('should track hits and misses', async () => {
      await cache.set('key1', 'value1');
      
      // Hit
      await cache.get('key1');
      let stats = cache.getStats();
      expect(stats.hits).toBe(1);
      expect(stats.misses).toBe(0);
      
      // Miss
      await cache.get('nonexistent');
      stats = cache.getStats();
      expect(stats.hits).toBe(1);
      expect(stats.misses).toBe(1);
      
      // Hit rate
      expect(stats.hitRate).toBe(0.5);
    });

    it('should track cache size', async () => {
      let stats = cache.getStats();
      expect(stats.size).toBe(0);
      
      await cache.set('key1', 'value1');
      await cache.set('key2', 'value2');
      
      stats = cache.getStats();
      expect(stats.size).toBe(2);
    });

    it('should handle zero requests', () => {
      const stats = cache.getStats();
      expect(stats.hits).toBe(0);
      expect(stats.misses).toBe(0);
      expect(stats.hitRate).toBe(0);
    });
  });

  describe('edge cases', () => {
    it('should handle null values', async () => {
      await cache.set('key1', null as any);
      const value = await cache.get('key1');
      expect(value).toBeNull();
    });

    it('should handle undefined values', async () => {
      await cache.set('key1', undefined as any);
      const value = await cache.get('key1');
      expect(value).toBeUndefined();
    });

    it('should handle empty string keys', async () => {
      await cache.set('', 'empty key');
      const value = await cache.get('');
      expect(value).toBe('empty key');
    });
  });
});

describe('RequestCache', () => {
  let requestCache: RequestCache;

  beforeEach(() => {
    requestCache = new RequestCache({
      ttl: 60000,
      maxSize: 100
    });
  });

  describe('caching behavior', () => {
    it('should cache successful requests', async () => {
      const testData = { data: 'test' };
      
      // First call - cache miss
      const result1 = await requestCache.get('test-url');
      expect(result1).toBeNull();
      
      // Set data in cache
      await requestCache.set('test-url', testData);
      
      // Second call - cache hit
      const result2 = await requestCache.get('test-url');
      expect(result2).toEqual(testData);
    });

    it('should support set and get operations', async () => {
      const testData = { data: 'test' };
      
      // Set data
      await requestCache.set('test-url', testData);
      
      // Get data
      const result = await requestCache.get('test-url');
      expect(result).toEqual(testData);
    });

    it('should handle cache misses', async () => {
      // Get non-existent data
      const result = await requestCache.get('non-existent');
      expect(result).toBeNull();
    });
  });

  describe('cache key generation', () => {
    it('should use URL as cache key', async () => {
      const data1 = { data: 'test1' };
      const data2 = { data: 'test2' };
      
      await requestCache.set('url1', data1);
      await requestCache.set('url2', data2);
      
      expect(await requestCache.get('url1')).toEqual(data1);
      expect(await requestCache.get('url2')).toEqual(data2);
    });
  });

  describe('delete operation', () => {
    it('should delete cached data', async () => {
      const testData = { data: 'test' };
      
      await requestCache.set('url1', testData);
      expect(await requestCache.get('url1')).toEqual(testData);
      
      await requestCache.delete('url1');
      expect(await requestCache.get('url1')).toBeNull();
    });
  });

  describe('cache with options', () => {
    it('should handle cache with options parameter', async () => {
      const testData = { data: 'test' };
      // Options parameter test - options not directly used but validates signature
      
      // Set with proper parameter order: url, response, options, ttl
      await requestCache.set('url1', testData, undefined, 3600000);
      
      // Get without options
      const result = await requestCache.get('url1');
      expect(result).toEqual(testData);
    });
  });
});