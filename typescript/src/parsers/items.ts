/**
 * Typed item identifiers for SEC filings.
 *
 * Each enum value is the SEC item number, so the enums are usable
 * anywhere a raw item number string is accepted (`getItem`,
 * `extractSpecificItems`, `EightK.hasItem`, ...).
 */

/** 10-K items by name; each value is the SEC item number. */
export enum TenKItem {
  BUSINESS = "1",
  RISK_FACTORS = "1A",
  UNRESOLVED_STAFF_COMMENTS = "1B",
  CYBERSECURITY = "1C",
  PROPERTIES = "2",
  LEGAL_PROCEEDINGS = "3",
  MINE_SAFETY_DISCLOSURES = "4",
  MARKET_FOR_COMMON_EQUITY = "5",
  RESERVED = "6",
  MANAGEMENT_DISCUSSION_AND_ANALYSIS = "7",
  MARKET_RISK_DISCLOSURES = "7A",
  FINANCIAL_STATEMENTS = "8",
  ACCOUNTANT_CHANGES_AND_DISAGREEMENTS = "9",
  CONTROLS_AND_PROCEDURES = "9A",
  OTHER_INFORMATION = "9B",
  FOREIGN_JURISDICTION_DISCLOSURES = "9C",
  DIRECTORS_AND_GOVERNANCE = "10",
  EXECUTIVE_COMPENSATION = "11",
  SECURITY_OWNERSHIP = "12",
  RELATED_TRANSACTIONS = "13",
  ACCOUNTANT_FEES = "14",
  EXHIBITS = "15",
}

/** 10-Q items by name; Part II items carry the `II-` prefix. */
export enum TenQItem {
  FINANCIAL_STATEMENTS = "1",
  MANAGEMENT_DISCUSSION_AND_ANALYSIS = "2",
  MARKET_RISK_DISCLOSURES = "3",
  CONTROLS_AND_PROCEDURES = "4",
  LEGAL_PROCEEDINGS = "II-1",
  RISK_FACTORS = "II-1A",
  UNREGISTERED_SALES = "II-2",
  DEFAULTS_UPON_SENIOR_SECURITIES = "II-3",
  MINE_SAFETY_DISCLOSURES = "II-4",
  OTHER_INFORMATION = "II-5",
  EXHIBITS = "II-6",
}

/** 8-K items by name; each value is the SEC item number. */
export enum EightKItem {
  MATERIAL_AGREEMENT = "1.01",
  MATERIAL_AGREEMENT_TERMINATION = "1.02",
  ACQUISITION_OR_DISPOSITION = "2.01",
  RESULTS_OF_OPERATIONS = "2.02",
  DIRECT_FINANCIAL_OBLIGATION = "2.03",
  DELISTING_NOTICE = "3.01",
  UNREGISTERED_SALES = "3.02",
  ACCOUNTANT_CHANGES = "4.01",
  NON_RELIANCE_ON_FINANCIALS = "4.02",
  CONTROL_CHANGES = "5.01",
  OFFICER_AND_DIRECTOR_CHANGES = "5.02",
  BYLAW_AMENDMENTS = "5.03",
  REGULATION_FD_DISCLOSURE = "7.01",
  OTHER_EVENTS = "8.01",
  FINANCIAL_STATEMENTS_AND_EXHIBITS = "9.01",
}

/** Any of the typed item identifiers accepted alongside plain strings. */
export type FilingItem = TenKItem | TenQItem | EightKItem;
