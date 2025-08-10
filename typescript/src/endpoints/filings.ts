/**
 * Filing endpoints for SEC EDGAR API
 */

import { HttpClient } from '../utils';
import { CompanySubmissions, RequestOptions } from '../types';

const SEC_BASE_URL = 'https://data.sec.gov';

export class FilingsEndpoints {
  private httpClient: HttpClient;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  async getCompanySubmissions(
    cik: string | number,
    options: RequestOptions = {}
  ): Promise<CompanySubmissions> {
    const cikStr = typeof cik === 'number' ? cik.toString().padStart(10, '0') : cik.padStart(10, '0');
    const url = `${SEC_BASE_URL}/submissions/CIK${cikStr}.json`;
    
    let submissions = await this.httpClient.get(url);
    
    // Apply filters if provided
    if (options.submissionType || options.fromDate || options.toDate) {
      submissions = this.filterSubmissions(submissions, options);
    }
    
    return submissions;
  }

  async getFiling(cik: string | number, accessionNumber: string): Promise<Record<string, any>> {
    const cikStr = typeof cik === 'number' ? cik.toString().padStart(10, '0') : cik.padStart(10, '0');
    const accessionFormatted = accessionNumber.replace(/-/g, '');
    const url = `${SEC_BASE_URL}/Archives/edgar/data/${parseInt(cikStr)}/${accessionFormatted}/${accessionNumber}-index.json`;
    
    return await this.httpClient.get(url);
  }

  private filterSubmissions(
    submissions: CompanySubmissions,
    options: RequestOptions
  ): CompanySubmissions {
    if (!submissions.filings || !submissions.filings.recent) {
      return submissions;
    }
    
    const { recent } = submissions.filings;
    let indices = recent.accessionNumber.map((_: any, index: number) => index);
    
    // Filter by submission type
    if (options.submissionType) {
      indices = indices.filter((i: number) => 
        recent.form[i] === options.submissionType
      );
    }
    
    // Filter by date range
    if (options.fromDate || options.toDate) {
      indices = indices.filter((i: number) => {
        const filingDate = recent.filingDate[i];
        if (options.fromDate && filingDate < options.fromDate) return false;
        if (options.toDate && filingDate > options.toDate) return false;
        return true;
      });
    }
    
    // Create filtered results
    const filteredRecent: Record<string, any> = {};
    Object.keys(recent).forEach(key => {
      filteredRecent[key] = indices.map((i: number) => recent[key][i]);
    });
    
    return {
      ...submissions,
      filings: {
        ...submissions.filings,
        recent: filteredRecent
      }
    };
  }
}