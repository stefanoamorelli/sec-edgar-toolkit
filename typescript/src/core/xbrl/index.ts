/**
 * XBRL access for one filing: fact queries and rendered-report statements.
 */

export { XBRLInstance, XbrlFilingLike, XbrlApiLike } from "./instance";
export { buildFactRecords, factsHistory, FactHistoryRow } from "./queries";
export { RenderedReportReader, ReportDescriptor } from "./rendered-reports";
export {
  parseReportHtml,
  parseReportNumber,
  normalizePeriodLabel,
  StatementLineItem,
} from "./report-html-parser";
export {
  STATEMENT_ALIASES,
  STATEMENT_CONCEPTS,
  normalizeStatementType,
} from "./statements";
