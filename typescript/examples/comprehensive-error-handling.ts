#!/usr/bin/env ts-node
/**
 * Comprehensive Error Handling Example
 * 
 * This example demonstrates the new error handling capabilities:
 * 1. Specific error types for different scenarios
 * 2. Error recovery and retry logic
 * 3. Proper error context and debugging information
 */

import { createClient } from '../src';
import {
    CompanyNotFoundError,
    InvalidUserAgentError,
    RateLimitError,
    FilingNotFoundError,
    InvalidFormTypeError,
    ErrorHandler
} from '../src/exceptions';

async function main() {
    console.log('SEC EDGAR Toolkit - Error Handling Examples\n');
    
    // Example 1: Invalid User Agent
    console.log('1. Testing Invalid User Agent Error:');
    console.log('-'.repeat(50));
    try {
        const badClient = createClient({
            userAgent: 'Bot' // Too short, missing contact info
        });
    } catch (error) {
        if (error instanceof InvalidUserAgentError) {
            console.log(`✓ Caught InvalidUserAgentError: ${error.message}`);
            console.log(`  Field: ${error.field}`);
        }
    }
    
    // Create a valid client for remaining examples
    const client = createClient({
        userAgent: 'ErrorHandlingDemo/1.0 (demo@example.com)'
    });
    
    // Example 2: Company Not Found
    console.log('\n2. Testing Company Not Found Error:');
    console.log('-'.repeat(50));
    try {
        const company = await client.companies.lookup('INVALID_TICKER_XYZ');
        // This line should not execute
        console.log('Found company:', company);
    } catch (error) {
        if (error instanceof CompanyNotFoundError) {
            console.log(`✓ Caught CompanyNotFoundError: ${error.message}`);
            console.log(`  Identifier: ${error.identifier}`);
            console.log(`  Search Type: ${error.searchType}`);
        }
    }
    
    // Example 3: Invalid Form Type
    console.log('\n3. Testing Invalid Form Type Error:');
    console.log('-'.repeat(50));
    try {
        // Get a real company first
        const apple = await client.companies.lookup('AAPL');
        if (apple) {
            // Try to get an invalid form type
            const filings = await apple.filings
                .formTypes(['INVALID-FORM'])
                .fetch();
        }
    } catch (error) {
        if (error instanceof InvalidFormTypeError) {
            console.log(`✓ Caught InvalidFormTypeError: ${error.message}`);
            console.log(`  Valid form types: ${error.validTypes?.join(', ')}`);
        }
    }
    
    // Example 4: Error Recovery with Retry Logic
    console.log('\n4. Testing Error Recovery and Retry Logic:');
    console.log('-'.repeat(50));
    
    // Simulate a retryable error scenario
    let attemptCount = 0;
    const maxAttempts = 3;
    
    async function fetchWithRetry() {
        attemptCount++;
        console.log(`  Attempt ${attemptCount}/${maxAttempts}...`);
        
        try {
            // This would normally be a real API call
            if (attemptCount < 2) {
                // Simulate a network error on first attempt
                throw new Error('ECONNREFUSED');
            }
            
            // Success on second attempt
            const company = await client.companies.lookup('MSFT');
            return company;
            
        } catch (error: any) {
            // Check if error is retryable
            if (ErrorHandler.isRetryable(error) && attemptCount < maxAttempts) {
                const delay = ErrorHandler.getRetryDelay(error, attemptCount);
                console.log(`  Retryable error detected. Waiting ${delay}ms before retry...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return fetchWithRetry();
            }
            throw error;
        }
    }
    
    try {
        const company = await fetchWithRetry();
        console.log(`✓ Successfully fetched after ${attemptCount} attempts`);
        if (company) {
            console.log(`  Found: ${company.name}`);
        }
    } catch (error) {
        console.error('Failed after all retry attempts:', error);
    }
    
    // Example 5: Error Context and Debugging
    console.log('\n5. Testing Error Context and Debugging:');
    console.log('-'.repeat(50));
    
    try {
        // Create an error with context
        const error = new Error('Database connection failed');
        const wrappedError = ErrorHandler.wrapError(error, {
            operation: 'fetchCompanyFilings',
            cik: '0000320193',
            ticker: 'AAPL',
            formType: '10-K',
            url: 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'
        }, 'Failed to fetch company filings due to database error');
        
        throw wrappedError;
        
    } catch (error: any) {
        console.log(`✓ Caught error with context:`);
        console.log(`  ${error.toString()}`);
        console.log(`  Original error: ${error.originalError?.message}`);
        console.log('\n  Context details:');
        Object.entries(error.context || {}).forEach(([key, value]) => {
            console.log(`    ${key}: ${value}`);
        });
    }
    
    // Example 6: Rate Limit Handling
    console.log('\n6. Testing Rate Limit Error Handling:');
    console.log('-'.repeat(50));
    
    const rateLimitError = new RateLimitError('Rate limit exceeded: Too many requests');
    console.log(`✓ Created RateLimitError: ${rateLimitError.message}`);
    console.log(`  Status Code: ${rateLimitError.statusCode}`);
    console.log(`  Is Retryable: ${ErrorHandler.isRetryable(rateLimitError)}`);
    console.log(`  Suggested Retry Delay: ${ErrorHandler.getRetryDelay(rateLimitError, 1)}ms`);
    
    console.log('\n✅ All error handling examples completed successfully!');
}

// Run the example
main().catch(error => {
    console.error('\n❌ Unhandled error:', error);
    process.exit(1);
});