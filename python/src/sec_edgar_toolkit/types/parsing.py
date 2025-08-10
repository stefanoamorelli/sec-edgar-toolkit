"""Type definitions for parsing infrastructure."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TypedDict, Union


class DocumentSection(TypedDict):
    """Document section information."""

    name: str
    content: str
    start_index: int
    end_index: int
    type: str  # 'text', 'table', 'xbrl', 'exhibit'


class TableMetadata(TypedDict):
    """Table metadata information."""

    location: str
    format: str  # 'html', 'text', 'xbrl'


class Table(TypedDict):
    """Parsed table information."""

    title: str
    headers: List[str]
    rows: List[List[str]]
    metadata: TableMetadata


class Exhibit(TypedDict):
    """Exhibit information."""

    number: str
    title: str
    description: str
    filename: str
    type: str
    content: Optional[str]


class DocumentMetadata(TypedDict):
    """Document metadata information."""

    document_count: int
    has_xbrl: bool
    has_html: bool
    file_size: int
    processing_time: float
    parsing_errors: List[str]


class ParsedDocument(TypedDict):
    """Complete parsed document data."""

    form_type: str
    filing_date: datetime
    cik: str
    company_name: str
    accession_number: str
    raw_content: str
    sections: List[DocumentSection]
    tables: List[Table]
    exhibits: List[Exhibit]
    metadata: DocumentMetadata


class Metric(TypedDict):
    """Extracted metric information."""

    name: str
    value: Union[float, str]
    units: str
    confidence: float
    source: str


class Statement(TypedDict):
    """Extracted statement information."""

    type: str  # 'forward_looking', 'risk_factor', 'material_change'
    content: str
    confidence: float
    location: str


class ValidationError(TypedDict):
    """Validation error information."""

    type: str
    message: str
    location: str
    severity: str  # 'error', 'warning', 'info'


class ValidationWarning(TypedDict):
    """Validation warning information."""

    type: str
    message: str
    location: str


class ValidationResult(TypedDict):
    """Validation result information."""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
