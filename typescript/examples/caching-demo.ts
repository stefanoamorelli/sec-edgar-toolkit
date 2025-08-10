#!/usr/bin/env ts-node
/**
 * Caching System Demo
 * 
 * This example demonstrates the caching capabilities:
 * 1. Automatic request caching
 * 2. Cache hit/miss statistics
 * 3. Manual cache management
 * 4. Performance improvements with caching
 */

import { createClient } from '../src';
import { Cache } from '../src/utils/cache';

async function measureTime<T>(
    operation: () => Promise<T>,
    label: string
): Promise<{ result: T; duration: number }> {
    const start = Date.now();
    const result = await operation();
    const duration = Date.now() - start;
    console.log(`  ${label}: ${duration}ms`);
    return { result, duration };
}

async function main() {
    console.log('SEC EDGAR Toolkit - Caching System Demo\n');
    
    // Initialize client with caching enabled (default)
    const client = createClient({
        userAgent: 'CachingDemo/1.0 (demo@example.com)',
        cache: {
            ttl: 300000, // 5 minutes
            maxSize: 100,
            persistent: false // Use memory cache for demo
        }
    });
    
    // Example 1: Automatic Request Caching
    console.log('1. Automatic Request Caching:');
    console.log('-'.repeat(50));
    
    // First request - cache miss
    console.log('First request (cache miss):');
    const { result: company1, duration: duration1 } = await measureTime(
        () => client.companies.lookup('AAPL'),
        'Company lookup'
    );
    console.log(`  Found: ${company1?.name}`);
    
    // Second request - cache hit
    console.log('\nSecond request (cache hit):');
    const { result: company2, duration: duration2 } = await measureTime(
        () => client.companies.lookup('AAPL'),
        'Company lookup'
    );
    console.log(`  Found: ${company2?.name}`);
    console.log(`  ✓ Speed improvement: ${((duration1 - duration2) / duration1 * 100).toFixed(1)}%`);
    
    // Example 2: Filing Data Caching
    console.log('\n2. Filing Data Caching:');
    console.log('-'.repeat(50));
    
    if (company1) {
        // First filing fetch - cache miss
        console.log('First filing fetch (cache miss):');
        const { result: filings1, duration: filingDuration1 } = await measureTime(
            () => company1.filings.formTypes(['10-K']).recent(5).fetch(),
            'Filing fetch'
        );
        console.log(`  Found ${filings1.length} filings`);
        
        // Second filing fetch - cache hit
        console.log('\nSecond filing fetch (cache hit):');
        const { result: filings2, duration: filingDuration2 } = await measureTime(
            () => company1.filings.formTypes(['10-K']).recent(5).fetch(),
            'Filing fetch'
        );
        console.log(`  Found ${filings2.length} filings`);
        console.log(`  ✓ Speed improvement: ${((filingDuration1 - filingDuration2) / filingDuration1 * 100).toFixed(1)}%`);
    }
    
    // Example 3: Manual Cache Management
    console.log('\n3. Manual Cache Management:');
    console.log('-'.repeat(50));
    
    // Create a custom cache instance
    const customCache = new Cache<any>({
        ttl: 60000, // 1 minute
        maxSize: 50
    });
    
    // Add items to cache
    console.log('Adding items to cache:');
    await customCache.set('company:TSLA', { name: 'Tesla, Inc.', cik: '0001318605' });
    await customCache.set('company:NVDA', { name: 'NVIDIA Corporation', cik: '0001045810' });
    await customCache.set('company:AMZN', { name: 'Amazon.com, Inc.', cik: '0001018724' });
    
    // Get cache statistics
    const stats = customCache.getStats();
    console.log(`  Cache size: ${stats.size} items`);
    console.log(`  Hit rate: ${(stats.hitRate * 100).toFixed(1)}%`);
    console.log(`  Hits: ${stats.hits}, Misses: ${stats.misses}`);
    
    // Test cache retrieval
    console.log('\nRetrieving from cache:');
    const tesla = await customCache.get('company:TSLA');
    console.log(`  Tesla: ${tesla ? '✓ Found' : '✗ Not found'}`);
    
    const invalid = await customCache.get('company:INVALID');
    console.log(`  Invalid: ${invalid ? '✓ Found' : '✗ Not found'}`);
    
    // Update cache statistics
    const updatedStats = customCache.getStats();
    console.log(`\nUpdated statistics:`);
    console.log(`  Hit rate: ${(updatedStats.hitRate * 100).toFixed(1)}%`);
    console.log(`  Hits: ${updatedStats.hits}, Misses: ${updatedStats.misses}`);
    
    // Example 4: Cache Eviction (LRU)
    console.log('\n4. Cache Eviction (LRU):');
    console.log('-'.repeat(50));
    
    // Create a small cache to demonstrate eviction
    const smallCache = new Cache<string>({
        ttl: 60000,
        maxSize: 3
    });
    
    console.log('Adding items to small cache (max size: 3):');
    await smallCache.set('item1', 'First item');
    await smallCache.set('item2', 'Second item');
    await smallCache.set('item3', 'Third item');
    console.log(`  Cache size: ${smallCache.getStats().size}`);
    
    // Access item1 to make it recently used
    await smallCache.get('item1');
    console.log('  Accessed item1 (now most recently used)');
    
    // Add a fourth item - should evict least recently used (item2)
    await smallCache.set('item4', 'Fourth item');
    console.log('\nAfter adding item4:');
    console.log(`  Cache size: ${smallCache.getStats().size}`);
    console.log(`  item1: ${await smallCache.get('item1') ? '✓ Present' : '✗ Evicted'}`);
    console.log(`  item2: ${await smallCache.get('item2') ? '✓ Present' : '✗ Evicted'}`);
    console.log(`  item3: ${await smallCache.get('item3') ? '✓ Present' : '✗ Evicted'}`);
    console.log(`  item4: ${await smallCache.get('item4') ? '✓ Present' : '✗ Evicted'}`);
    
    // Example 5: Cache Performance Benefits
    console.log('\n5. Cache Performance Benefits:');
    console.log('-'.repeat(50));
    
    // Simulate multiple requests for the same data
    const tickers = ['AAPL', 'MSFT', 'GOOGL', 'AAPL', 'MSFT', 'AAPL'];
    const timings: number[] = [];
    
    console.log('Fetching company data multiple times:');
    for (const ticker of tickers) {
        const { duration } = await measureTime(
            () => client.companies.lookup(ticker),
            `  ${ticker}`
        );
        timings.push(duration);
    }
    
    const avgFirstRequest = (timings[0] + timings[1] + timings[2]) / 3;
    const avgCachedRequest = (timings[3] + timings[4] + timings[5]) / 3;
    
    console.log(`\nPerformance Summary:`);
    console.log(`  Average first request: ${avgFirstRequest.toFixed(0)}ms`);
    console.log(`  Average cached request: ${avgCachedRequest.toFixed(0)}ms`);
    console.log(`  ✓ Overall speed improvement: ${((avgFirstRequest - avgCachedRequest) / avgFirstRequest * 100).toFixed(1)}%`);
    
    console.log('\n✅ Caching demo completed successfully!');
}

// Run the example
main().catch(console.error);