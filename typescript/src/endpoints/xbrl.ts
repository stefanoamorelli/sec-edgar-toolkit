/**
 * XBRL endpoints for SEC EDGAR API
 */

import { HttpClient } from '../utils';
import { RequestOptions } from '../types';

const SEC_BASE_URL = 'https://data.sec.gov';

export class XbrlEndpoints {
  private httpClient: HttpClient;

  constructor(httpClient: HttpClient) {
    this.httpClient = httpClient;
  }

  async getCompanyFacts(cik: string | number): Promise<Record<string, any>> {
    const cikStr = typeof cik === 'number' ? cik.toString().padStart(10, '0') : cik.padStart(10, '0');
    const url = `${SEC_BASE_URL}/api/xbrl/companyfacts/CIK${cikStr}.json`;
    
    return await this.httpClient.get(url);
  }

  async getCompanyConcept(
    cik: string | number,
    taxonomy: string,
    tag: string,
    unit?: string
  ): Promise<Record<string, any>> {
    const cikStr = typeof cik === 'number' ? cik.toString().padStart(10, '0') : cik.padStart(10, '0');
    let url = `${SEC_BASE_URL}/api/xbrl/companyconcept/CIK${cikStr}/${taxonomy}/${tag}.json`;
    
    if (unit) {
      url += `?unit=${encodeURIComponent(unit)}`;
    }
    
    return await this.httpClient.get(url);
  }

  async getFrames(
    taxonomy: string,
    tag: string,
    unit: string,
    year: number,
    options: RequestOptions = {}
  ): Promise<Record<string, any>> {
    let period = year.toString();
    
    if (options.quarter) {
      period += `Q${options.quarter}`;
    } else if (options.instantaneous) {
      period += 'I';
    }
    
    const url = `${SEC_BASE_URL}/api/xbrl/frames/${taxonomy}/${tag}/${unit}/${period}.json`;
    
    return await this.httpClient.get(url);
  }
}