/**
 * Type definitions for parsing infrastructure
 */

export interface ParsedDocument {
  formType: string;
  filingDate: Date;
  cik: string;
  companyName: string;
  accessionNumber: string;
  rawContent: string;
  sections: DocumentSection[];
  tables: Table[];
  exhibits: Exhibit[];
  metadata: DocumentMetadata;
}

export interface DocumentSection {
  name: string;
  content: string;
  startIndex: number;
  endIndex: number;
  type: 'text' | 'table' | 'xbrl' | 'exhibit';
}

export interface Table {
  title: string;
  headers: string[];
  rows: string[][];
  metadata: {
    location: string;
    format: 'html' | 'text' | 'xbrl';
  };
}

export interface Exhibit {
  number: string;
  title: string;
  description: string;
  filename: string;
  type: string;
  content?: string;
}

export interface DocumentMetadata {
  documentCount: number;
  hasXBRL: boolean;
  hasHTML: boolean;
  fileSize: number;
  processingTime: number;
  parsingErrors: string[];
}

export interface Metric {
  name: string;
  value: number | string;
  units: string;
  confidence: number;
  source: string;
}

export interface Statement {
  type: 'forward_looking' | 'risk_factor' | 'material_change';
  content: string;
  confidence: number;
  location: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ParsingValidationError[];
  warnings: ValidationWarning[];
}

export interface ParsingValidationError {
  type: string;
  message: string;
  location: string;
  severity: 'error' | 'warning' | 'info';
}

export interface ValidationWarning {
  type: string;
  message: string;
  location: string;
}