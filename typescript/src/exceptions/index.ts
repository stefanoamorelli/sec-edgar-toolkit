/**
 * Exception exports for SEC EDGAR Toolkit
 */

export {
  SecEdgarApiError,
  RateLimitError,
  AuthenticationError,
  NotFoundError
} from './base';

export {
  // Configuration errors
  ConfigurationError,
  InvalidUserAgentError,
  
  // Request errors
  RequestError,
  TimeoutError,
  NetworkError,
  
  // Validation errors
  ValidationError,
  InvalidCIKError,
  InvalidDateError,
  InvalidFormTypeError,
  
  // Company errors
  CompanyNotFoundError,
  MultipleCompaniesFoundError,
  
  // Filing errors
  FilingNotFoundError,
  FilingContentError,
  
  // Parsing errors
  ParsingError,
  XMLParsingError,
  JSONParsingError,
  
  // XBRL errors
  XBRLError,
  ConceptNotFoundError,
  InvalidUnitError,
  
  // Cache errors
  CacheError,
  
  // Error utilities
  ErrorContext,
  ErrorWithContext,
  ErrorHandler
} from './errors';