/**
 * Filing-related type definitions
 */

export interface FilingDocument {
  sequence?: string;
  filename?: string;
  description?: string;
  type?: string;
  size?: number;
}

export interface FilingDetail {
  accessionNumber: string;
  filingDate: string;
  reportDate?: string;
  acceptanceDateTime: string;
  act?: string;
  form: string;
  fileNumber: string;
  filmNumber?: string;
  items?: string;
  size: number;
  isXBRL: boolean;
  isInlineXBRL: boolean;
  primaryDocument: string;
  primaryDocDescription: string;
}